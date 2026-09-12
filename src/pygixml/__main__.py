"""
python -m pygixml <subcommand> [OPTIONS] [ARGS]

Subcommands:
    query           Query XML files with XPath or dotted notation (loads full DOM)
    jsonify (json)  Convert XML to JSON (auto-streams for big files, O(1) memory)
    stream          Stream matching elements from huge XML as JSON, one record
                    at a time (bounded memory) -- like a jq/xq filter for XML
                    too large to load as a whole
    cat             Pretty-print (and colorize, if colorama is installed) an
                    XML file for the terminal
    convert         Convert a file between XML, JSON, YAML, and TOON
"""

import sys


def main():
    if len(sys.argv) < 2:
        sys.stdout.write(__doc__.strip() + "\n")
        sys.exit(1)

    subcommand = sys.argv[1]
    # Remove the subcommand from argv so the submodule sees clean args
    sys.argv = [f"pygixml {subcommand}"] + sys.argv[2:]

    if subcommand == "query":
        from pygixml.query import main as query_main
        sys.exit(query_main())

    elif subcommand in ("jsonify", "json"):
        from pygixml.jsoncmd import main as json_main
        sys.exit(json_main())

    elif subcommand == "stream":
        from pygixml.streamcmd import main as stream_main
        sys.exit(stream_main())

    elif subcommand == "cat":
        from pygixml.catcmd import main as cat_main
        sys.exit(cat_main())

    elif subcommand == "convert":
        from pygixml.convertcmd import main as convert_main
        sys.exit(convert_main())

    elif subcommand in ("-h", "--help", "help"):
        sys.stdout.write(__doc__.strip() + "\n")
        sys.exit(0)

    elif subcommand in ("-v", "--version", "version"):
        from pygixml import __version__
        sys.stdout.write(f"pygixml {__version__}\n")
        sys.exit(0)

    else:
        sys.stderr.write(f"pygixml: unknown subcommand {subcommand!r}\n")
        sys.stderr.write("Available subcommands: query, jsonify, stream, cat, convert\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
