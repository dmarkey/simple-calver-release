#!/usr/bin/python3
import sys
import json
import os
from subprocess import check_output, CalledProcessError
from time import strftime


def write_release_version_output(release_version):
    output_file = os.getenv('GITHUB_OUTPUT')
    with open(output_file, "a") as outputs:
        outputs.write(f"released-version={release_version}")


def attempt_hotfix_release(version, release_branch, mainline_branch, create_prs_for_hotfixes_to_mainline=True):
    check_output(
        ["gh", "release", "create", version, "--target", release_branch, "--generate-notes", "-t",
         f"Automated Hotfix Release {version}"])
    write_release_version_output(version)
    if create_prs_for_hotfixes_to_mainline:
        check_output(["gh",
                      "pr",
                      "create",
                      "--title",
                      f"Automated Hotfix PR to {mainline_branch} from {release_branch}",
                      "--body",
                      f"From release {version}",
                      "--base", mainline_branch,
                      "--head", release_branch])


def attempt_standard_release(release_branch, version_prefix, iterate_minor=True):
    iterator = 0

    while True:
        try:
            version_number = f"{version_prefix}.{iterator}.0"
            check_output(
                ["gh", "release", "create", version_number, "--target", release_branch, "--generate-notes", "-t",
                 f"Automated Release {version_number}"])
        except CalledProcessError:
            if not iterate_minor:
                raise
            else:
                iterator += 1
        else:
            print(f"Successfully released {release_branch} as {version_number}")
            write_release_version_output(version_number)
            return


def release(pr_number, version_scheme, mainline_branch, create_prs_for_hotfixes_to_mainline):
    check_output(["git", "config", "--global", "--add", "safe.directory", "/github/workspace"])
    result = check_output(["gh", "pr", "view", pr_number, "-c", "--json", "baseRefName,comments,labels,mergedAt"])
    result_parsed = json.loads(result)
    if result_parsed['mergedAt'] is None:
        raise Exception(f"PR {pr_number} is not merged.")
    plain_labels = [x['name'] for x in result_parsed['labels']]
    if "skip-release" in plain_labels:
        print("'skip-release' label present, skipping this release.")
        return
    if result_parsed['baseRefName'] == mainline_branch:
        version_prefix = strftime(version_scheme)
        attempt_standard_release(mainline_branch, version_prefix)
    else:
        if not [x for x in result_parsed['labels'] if x['name'] == "is-hotfix"]:
            print("Missing hotfix label, assuming this isn't for release.")
            return
        hotfix_branch = result_parsed['baseRefName']
        hotfix_version = hotfix_branch[:-7]
        print(f"Attempting for branch {result_parsed['baseRefName']}, version {hotfix_version}")
        attempt_hotfix_release(hotfix_version, hotfix_branch, mainline_branch,
                               create_prs_for_hotfixes_to_mainline=create_prs_for_hotfixes_to_mainline)


if __name__ == "__main__":
    _pr_number = sys.argv[1]
    _version_scheme = sys.argv[2]
    _mainline_branch = sys.argv[3]
    _create_prs_for_hotfixes_to_mainline = (sys.argv[4] == "true")
    release(_pr_number, _version_scheme, _mainline_branch, _create_prs_for_hotfixes_to_mainline)
