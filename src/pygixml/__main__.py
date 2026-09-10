"""
python -m pygixml <subcommand> [OPTIONS] [ARGS]

Subcommands:
    query    Query XML files with XPath or dotted notation (loads full DOM)
    json     Convert XML to JSON (auto-streams for big files, O(1) memory)
    stream   Stream matching elements from huge XML as JSON, one record
             at a time (bounded memory) -- like a jq/xq filter for XML
             too large to load as a whole
"""

import sys


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    subcommand = sys.argv[1]
    # Remove the subcommand from argv so the submodule sees clean args
    sys.argv = [f"pygixml {subcommand}"] + sys.argv[2:]

    if subcommand == "query":
        from pygixml.query import main as query_main
        sys.exit(query_main())

    elif subcommand == "json":
        from pygixml.jsoncmd import main as json_main
        sys.exit(json_main())

    elif subcommand == "stream":
        from pygixml.streamcmd import main as stream_main
        sys.exit(stream_main())

    elif subcommand in ("-h", "--help", "help"):
        print(__doc__.strip())
        sys.exit(0)

    elif subcommand in ("-v", "--version", "version"):
        from pygixml import __version__
        print(f"pygixml {__version__}")
        sys.exit(0)

    else:
        print(f"pygixml: unknown subcommand {subcommand!r}", file=sys.stderr)
        print("Available subcommands: query, json, stream", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
