# Traceroute analyzer
This tool intents to help the network engineers (or anyone else) to analyze the path of the traffic via the Internet alayzing the tracroute collected with MTR against the information available in the public data sources.

## Used public sources
- Peering DB
- IP API

## Usage
The script is aim to use with external resources. Peering DB doesn't require any authentication but IP API requieres an account (currently subscription is free). Create account and add your token to the `config.yml` file. Then:
1. Install the `requirements.txt`.
2. Run the tool as `python main.yml HOST TYPE`, where `HOST` is a destination (IPv4, IPv6 or FQDN) and `TYPE` is a transmission type `ipv4` or `ipv6`.

## Python
Tool was tested for Python 3.7, 3.8 and 3.9 versions.

## Information representation
- Traceroute showing the network graph based including IP addresses, loss per hop
- Map showing the geographical IP distribution (assuming that the information in Geo IP database is accurate.)

## Release notes
Version `0.2.1`:
- Rebuild of network topology function

Version `0.2.0`:
- First public release

Version `0.1.1`:
- Rebuild and simplifcaition

Version `0.1.0`:
- First release

(c)2021, Karneliuk.com