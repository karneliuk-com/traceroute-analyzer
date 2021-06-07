#!/usr/bin/env python
#(c)2021, Karneliuk.com

# Modules
import yaml
import sys
import os
import datetime

# Local artefacts
import bin.functions as bf


# Variables
config_file = "./config.yml"
config_ext = "./config_ext.yml"
destination = ("google.com", "ipv6")
cache_path = "./.cache"

# Body
if __name__ == "__main__":
    t1 = datetime.datetime.now()

    # Getting config
    try:
        config = yaml.load(open(config_file, "r").read(), Loader=yaml.Loader)

    except:
        t2 = datetime.datetime.now()
        print(f"Time elapsed: {t2 - t1}")

        sys.exit(f"Can't open the cofniguration file {config_file}.")

    try:
        new_config = yaml.load(open(config_ext, "r").read(), Loader=yaml.Loader)
        config = {**config, **new_config}

    except:
        print("Config isn't augmented with extra vars")

    # Checking the arguments
    if len(sys.argv) == 1:
        destination = destination
    elif len(sys.argv) == 2:
        destination = (sys.argv[1], "ipv4")
    elif len(sys.argv) == 3:
        destination = (sys.argv[1], sys.argv[2])

    else:
        sys.exit("Too many arguments are provided")

    # Checking cache folder
    if not os.path.exists(cache_path):
        os.mkdir(cache_path) 
        
    # Geting hops
    traceroute = bf.get_path(config ,*destination)

    # Augmenting data with info from external sources
    traceroute = bf.augment_data(traceroute, config, cache_path)

    # Build network graph
    topology = bf.build_graph(traceroute)

    # Build map
    bf.build_map(topology, config)

    # Build trace
    bf.build_isp(destination, topology, config)

    t2 = datetime.datetime.now()
    print(f"Time elapsed: {t2 - t1}")