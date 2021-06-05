#!/usr/bin/env python
#(c)2021, Karneliuk.com

# Modules
import yaml
import sys
import os


# Local artefacts
import bin.functions as bf


# Variables
config_file = "./config.yml"
destination = ("yandex.ru", "ipv6")
cache_path = "./.cache"

# Body
if __name__ == "__main__":
    # Getting config
    try:
        config = yaml.load(open(config_file, "r").read(), Loader=yaml.Loader)

    except:
        sys.exit(f"Can't open the cofniguration file {config_file}.")

    # Checking cache folder
    if not os.path.exists(cache_path):
        os.mkdir(cache_path) 
        
    # Geting hops
    traceroute = bf.get_path(*destination)

    # Augmenting data
    traceroute = bf.augment_data(traceroute, config, cache_path)

    # Build map
    bf.build_map(traceroute, config)

    # Build trace
    bf.build_isp(destination, traceroute, config)