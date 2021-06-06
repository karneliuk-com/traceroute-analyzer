#!/usr/bin/env python
#(c)2021, Karneliuk.com

# Modules
import subprocess
import json
import requests
import sys
from tqdm import tqdm
import folium
import re
from pyvis.network import Network
import os
import networkx


# User-defined functions
def get_path(cfg: dict, target: str, target_type: str = "ipv4") -> dict:
    """
    This function runs the MTR and collects its output in JSON format
    """
    allowed_types = {"ipv4", "ipv6"}

    if target_type not in allowed_types:
        sys.exit(f"Unsupported path type. Only {', '.join(allowed_types)} are supported.")

    result = []

    print(f"Tracing the path to {target} over {target_type}...")

    target_type = "-6" if target_type == "ipv6" else "-4"
    for run in tqdm(range(cfg["ecmp"]), desc=f"Collecting path info", colour="blue"):
        args = ["mtr", target_type, target, "-c", str(cfg["probes"]), "-B", str(run), "-n", "-z", "-j"]
        result_raw = subprocess.run(args=args, capture_output=True)
        
        if not result_raw.stderr:
            result.append(json.loads(result_raw.stdout.decode("utf-8")))

        else:
            sys.exit(f"There is some error with trace happened: {result_raw.stderr.decode('utf-8')}")

    print("Tracing completed.")

    return result


def get_link_color(link_loss: int) -> str:
    """
    This function returns the failure color code based on the percentage of the lost packets
    """
    result = ""

    failure_colors = [
        "#ffffff",
        "#ffeeee",
        "#ffdddd",
        "#ffcccc",
        "#ffbbbb",
        "#ffaaaa",
        "#ff8888",
        "#ff6666",
        "#ff4444",
        "#ff2222",
        "#ff0000"
    ]

    for i, fc in enumerate(failure_colors):
        if link_loss == float(i * 10):
            result = fc
        else:
            if link_loss > float(i * 10) and link_loss < float((i + 1) * 10):
                result = failure_colors[i + 1]

    return result


def augment_data(mtr_result: dict, geo_config: dict, cache_folder: str) -> dict:
    """
    This function augments the traceroute data with the external information collected via REST API
    """
    result = mtr_result

    # Augmenting the data
    for datasource_key, datasource_value in geo_config["datasources"].items():
        # Checking if local cache is existing
        if os.path.exists(f"{cache_folder}/{datasource_key}.json"):
            local_cache = json.loads(open(f"{cache_folder}/{datasource_key}.json", "r").read())

        else:
            local_cache = {}

        for run in tqdm(result, desc=f"Augnenting info", colour="blue"):
            for he in tqdm(run["report"]["hubs"], desc=f"Collecting {datasource_key} info", colour="green", leave=False):
                if datasource_key == "geo":
                    search_key = he['host']
                    url = f"{datasource_value['url']}/{search_key}?access_key={datasource_value['token']}"

                elif datasource_key == "isp":
                    search_key = re.sub('AS', '', he['ASN'])
                    url = f"{datasource_value['url']}/net?asn={search_key}"

                # Looking for AS entry in cache
                if search_key in local_cache:
                    he.update({datasource_key: local_cache[search_key]})

                # Making peering DB request
                else:
                    response = requests.get(url=url)

                    if response.status_code == 200:
                        try:
                            r = response.json()['data'][0] if datasource_key == "isp" else response.json()
                            he.update({datasource_key: r})
                            local_cache.update({search_key: r})

                        except json.decoder.JSONDecodeError as e:
                            he.update({datasource_key: {}})

                    # Creating empty entry if there is no match
                    else:
                        he.update({datasource_key: {}})

                # Updating the cache
                open(f"{cache_folder}/{datasource_key}.json", "w").write(json.dumps(local_cache, sort_keys=True, indent=4))

    return result


def build_graph(mtr_result: list) -> networkx.DiGraph():
    """
    This function builds the map of the traffic paths
    """
    result = networkx.DiGraph()
    groups = ["You"]
    
    # Adding starting node
    result.add_node(mtr_result[0]["report"]["mtr"]["src"], label=mtr_result[0]["report"]["mtr"]["src"], title="Trace start", level=0)
    
    # Adding transit hops
    for run in tqdm(mtr_result, desc=f"Building topology", colour="blue"):
        # Setting the starting point for the graph
        ph = mtr_result[0]["report"]["mtr"]["src"]

        for he in tqdm(run["report"]["hubs"], desc=f"Adding nodes to graph", colour="green", leave=False):
            if not result.has_node(he["host"]):
                isp_name = he["isp"]["name"] if he["isp"] else "Unknown ISP"
                asn = re.sub(r'AS', r'', he['ASN'])

                flag = f"{he['geo']['location']['country_flag_emoji']}" if "geo" in he and "location" in he["geo"] and "country_flag_emoji" in he["geo"]["location"] else "❓"

                title = f"ISP: {isp_name}<br>ASN: {asn}<br>IP: {he['host']}<br>{flag}"

                # Defining ISP Group
                if asn not in groups:
                    groups.append(asn)
                    group = len(groups) - 1

                else:
                    i = 0
                    while asn != groups[i]:
                        i += 1

                    group = i
                
                result.add_node(he["host"], label=he["host"], title=title, level=0, group=group, all_data=he)

            if not result.has_edge(ph, he["host"]):
                result.add_edge(ph, he["host"], title=f"Loss: {he['Loss%']}%<br>Latency: {he['Avg']} ms", color=get_link_color(he["Loss%"]), weight=1.5)

                # Updating the starting point for grpah
                ph = he["host"]

    return result


def build_isp2(target: str, G: networkx.DiGraph(), geo_config: dict) -> None:
    """
    This function builds the visual traceroute
    """
    nt = Network(height="600px", width="1200px", directed=True, bgcolor="#212121", font_color="#ffffff", 
                 layout=True, heading=f"Traceroute to {target[0]} over {target[1]}")

    nt.from_nx(G)
    nt.show(geo_config["result"]["file_asn"])


def build_map(mtr_result: dict, geo_config: dict) -> None:
    """
    This function builds the map of the trace
    """
    m = folium.Map()

    print("Drawing the map...")
    minus_one_hop = 0
    for index, entry in enumerate(mtr_result["report"]["hubs"]):
        if entry["geo"]:
            isp_name = entry["isp"]["name"] if entry["isp"] else "Unknown ISP"
            
            folium.Marker(
                location=[entry["geo"]["latitude"], entry["geo"]["longitude"]],
                popup=f"Hop: {entry['count']}<br>IP: {entry['host']}<br>Country: {entry['geo']['country_name']}<br>City: {entry['geo']['city']}<br>ASN: {re.sub('AS', '', entry['ASN'])}<br>ISP: {isp_name}",
                icon=folium.Icon(color="red")
            ).add_to(m)

            if index > 0 and mtr_result["report"]["hubs"][minus_one_hop]['geo']:
                folium.PolyLine(
                    locations=[(entry["geo"]["latitude"], entry["geo"]["longitude"]),(mtr_result["report"]["hubs"][minus_one_hop]["geo"]["latitude"], mtr_result["report"]["hubs"][minus_one_hop]["geo"]["longitude"])],
                    popup=f"Hop {entry['count']} -> Hop {mtr_result['report']['hubs'][minus_one_hop]['count']}",
                    color="red", weight=1.5
                ).add_to(m)

                minus_one_hop = index

    m.save(geo_config["result"]["file_map"])


def build_isp(target: str, mtr_result: dict, geo_config: dict) -> None:
    """
    This function builds the map of the trace
    """
    groups = ["You"]

    failure_colors = [
        "#ffffff",
        "#ffeeee",
        "#ffdddd",
        "#ffcccc",
        "#ffbbbb",
        "#ffaaaa",
        "#ff8888",
        "#ff6666",
        "#ff4444",
        "#ff2222",
        "#ff0000"
    ]

    print("Compiling the trace...")

    nt = Network(height="600px", width="1200px", directed=True, bgcolor="#212121", font_color="#ffffff", 
                 layout=True, heading=f"Traceroute to {target[0]} over {target[1]}")
    
    nt.add_node(0, label=mtr_result["report"]["mtr"]["src"], title="You", level=0)

    for he in mtr_result["report"]["hubs"]:
        isp_name = he["isp"]["name"] if he["isp"] else "Unknown ISP"
        asn = re.sub(r'AS', r'', he['ASN'])
        title = f"ISP: {isp_name}<br>ASN: {asn}<br>IP: {he['host']}"
        
        if asn not in groups:
            groups.append(asn)
            group = len(groups) - 1

        else:
            i = 0
            while asn != groups[i]:
                i += 1

            group = i

        for i, fc in enumerate(failure_colors):
            if he["Loss%"] == float(i * 10):
                lc = fc
            else:
                if he["Loss%"] > float(i * 10) and he["Loss%"] < float((i + 1) * 10):
                    lc = failure_colors[i + 1]
                
        nt.add_node(int(he["count"]), label=he["host"], title=title, level=group)
        nt.add_edge(int(he["count"]) - 1, int(he["count"]), title=f"Loss: {he['Loss%']}%<br>Latency: {he['Avg']} ms", color=lc, weight=1.5)

    nt.show(geo_config["result"]["file_asn"])