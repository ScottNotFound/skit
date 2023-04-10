import argparse
import sys
import re

import numpy as np


def pargs():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("celltile")
    parser.add_argument("-b", "--base", help="Set the new base as.")
    parser.add_argument("-k", "--kagome", help="Element on the kagome sites.")
    parser.add_argument("-i", "--interlayer", help="Element on the interlayer sites.")
    return parser.parse_args()


def herbertsmithite_hamming_ish_id(file, cell, new_base=None, kago=None, ilay=None):
    if kago is None:
        kago = "Cu"
    if ilay is None:
        ilay = "Zn"
    with open(file, "r") as f:
        txt = f.read()
    lines = txt.splitlines()
    i = 0
    j = -1
    for k, line in enumerate(lines):
        if line.lower().strip().startswith(r"%block positions_frac"):
            i = k
        if line.lower().strip().startswith(r"%endblock positions_frac"):
            j = k
    poslist = lines[i + 1 : j]
    posl = [
        (str(x[0]), tuple(map(float, x[1:])))
        for x in [line.strip().split() for line in poslist]
        if str(x[0]) in [kago, ilay]
    ]
    xyz = np.array([a for _, a in posl])
    basis = np.array([[1 / x] for x in cell if x > 1])
    basis_alt = np.array([[1 / x] for x in cell])
    base_site_ind = np.argwhere(
        (np.linalg.norm(xyz - 0.5, axis=1) - np.linalg.norm(basis / 2)) == 0
    )
    ks = base_site_ind.flatten()
    bs = xyz[ks]
    ks_ord = ks.copy()
    for d in range(2, -1, -1):
        ind = bs[:, d].argsort(kind="mergesort")
        bs = bs[ind]
        ks_ord = ks_ord[ind]
    base_sites = xyz[ks_ord]
    base_entries = [posl[k] for k in ks_ord]
    base_ids = [s == kago for s, _ in base_entries]
    base_str = "".join(map(str, map(int, base_ids)))
    if new_base is None:
        return base_str
    if "1" in base_str:
        print(f"Base cell must not have {kago} in interlayer.", file=sys.stderr)
        sys.exit(1)
    new_ids = [bool(int(i)) for i in new_base]
    if len(new_ids) != len(ks):
        print(
            "Something went wrong. Number of new entries different than number of base sites found."
        )
        sys.exit(1)
    flips = ks_ord[new_ids]
    unord_flip_ids = np.searchsorted(ks, flips)
    k = 0
    new_poslist = []
    for line in poslist:
        if ilay in line:
            if k in unord_flip_ids:
                new_poslist.append(re.sub(ilay, kago, line))
            else:
                new_poslist.append(line)
            k += 1
        else:
            new_poslist.append(line)
    return "\n".join(lines[: i + 1] + new_poslist + lines[j:])


def main():
    ns = pargs()
    cell = tuple(map(int, ns.celltile.split("x")))
    print(herbertsmithite_hamming_ish_id(ns.file, cell, ns.base, ns.kagome, ns.interlayer))
