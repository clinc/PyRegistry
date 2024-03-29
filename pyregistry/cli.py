#!/usr/bin/env python3
"""
Script entrypoint for copying images between registries.
"""

import argparse
import json
import logging
import pathlib
import re
import sys

from pyregistry import parse_image_name, parse_user, DockerCredentialStore


def main() -> None:
    """
    CLI entrypoint that copies an image between two registries.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    parser = argparse.ArgumentParser(
        description="Copy images between registries. If no dest image is given"
        " this will simply output the src manifest"
    )
    parser.add_argument("--src", required=True, help="Source registry image")
    parser.add_argument(
        "--src-user", required=False, default="", help="Source user:password basic auth"
    )
    parser.add_argument(
        "--src-ca", required=False, default=None, help="Source CA certificate"
    )
    parser.add_argument("--dst", required=False, help="Dest registry image")
    parser.add_argument(
        "--dst-user", required=False, default="", help="Dest user:password basic auth"
    )
    parser.add_argument(
        "--dst-ca", required=False, default=None, help="Dest CA certificate"
    )
    parser.add_argument(
        "--tag-pattern",
        action="append",
        help="Instead of just copying the given tag copy all tags matching a regex pattern",
    )
    parser.add_argument(
        "--auth-config",
        required=False,
        default="{}/.docker/config.json".format(pathlib.Path.home()),
        help="Path to Docker credential config file",
    )
    args = parser.parse_args()

    cred_store = None
    try:
        with open(args.auth_config, "r") as fconfig:
            cred_store = DockerCredentialStore(json.load(fconfig))
    except FileNotFoundError:
        pass

    src_manifest = parse_image_name(
        args.src,
        user=parse_user(args.src_user),
        verify=args.src_ca,
        cred_store=cred_store,
    )
    if not args.dst:
        if args.tag_pattern:
            result = {}
            for tag in src_manifest.registry.get_tags(src_manifest.repo):
                if not any(re.match(pat, tag) for pat in args.tag_pattern):
                    continue
                src_manifest.ref = tag
                result[tag] = src_manifest.manifest().content
        else:
            result = src_manifest.manifest().content
        json.dump(result, sys.stdout, indent=2)
        return

    dst_manifest = parse_image_name(
        args.dst,
        user=parse_user(args.dst_user),
        verify=args.dst_ca,
        cred_store=cred_store,
    )
    if args.tag_pattern:
        for tag in src_manifest.registry.get_tags(src_manifest.repo):
            if not any(re.match(pat, tag) for pat in args.tag_pattern):
                continue
            src_manifest.ref = tag
            dst_manifest.ref = tag
            print(f"Copying {src_manifest} to {dst_manifest}")
            src_manifest.copy(dst_manifest)
    else:
        src_manifest.copy(dst_manifest)
