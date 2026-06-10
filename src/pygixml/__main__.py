"""
python -m pygixml <subcommand> [OPTIONS] [ARGS]

Subcommands:
    query    Query XML files with XPath or dotted notation
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

    elif subcommand in ("-h", "--help", "help"):
        print(__doc__.strip())
        sys.exit(0)

    elif subcommand in ("-v", "--version", "version"):
        from pygixml import __version__
        print(f"pygixml {__version__}")
        sys.exit(0)

    else:
        print(f"pygixml: unknown subcommand {subcommand!r}", file=sys.stderr)
        print("Available subcommands: query", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
