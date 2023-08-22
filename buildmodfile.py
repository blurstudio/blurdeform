import re
import argparse
from pathlib import Path, PurePosixPath


def main(outpath, modname, modver, modpath):
    outpath = Path(outpath).absolute()
    modpath = modpath or modname

    basePath = outpath.parent
    plugPaths = list(basePath.glob(str(Path('**') / 'plug-ins')))

    lines = []
    for pp in plugPaths:
        rel = PurePosixPath(pp.relative_to(basePath))
        match = re.search(r"(?P<platform>win64|linux|mac)-(?P<year>\d+)", str(rel))
        if not match:
            continue
        plat, year = match['platform'], match['year']
        lines.append(f"+ PLATFORM:{plat} MAYAVERSION:{year} {modname} {modver} {modpath}")
        lines.append(f"plug-ins: {rel}")
        lines.append("")

    with open(outpath, 'w') as f:
        f.write('\n'.join(lines))


def parse():
    parser = argparse.ArgumentParser(
        prog='buildmodfile',
        description='builds a mod file ensuring that plugins are loaded for the proper maya versions',
    )
    parser.add_argument('outpath', help="The output filepath")
    parser.add_argument('-n', '--name', help="The name of the module", required=True)
    parser.add_argument('-v', '--version', help="The version of the module", default="1.0.0")
    parser.add_argument('-p', '--path', help="The relative path to the module")
    args = parser.parse_args()

    main(args.outpath, args.name, args.version, args.path)


if __name__ == "__main__":
    parse()


