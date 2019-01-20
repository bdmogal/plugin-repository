import argparse
import os
import sys
import json
from pprint import pprint
from distutils.version import LooseVersion, StrictVersion


PLUGIN_DISPLAY_TYPES = {
  'batchsource': 'Source',
  'streamingsource': 'Source',
  'batchsink': 'Sink',
  'sparksink': 'Sink',
  'transform': 'Transform',
  'splittertransform': 'Transform',
  'alertpublisher': 'Alert Publisher',
  'action': 'Action',
  'sparkprogram': 'Action',
  'postaction': 'Action',
  'batchaggregator': 'Analytics',
  'sparkcompute': 'Analytics',
  'windower': 'Analytics',
  'batchjoiner': 'Analytics',
  'condition': 'Condition',
  'errortransform': 'Error Handler'
}


class VersionRange:
  def __init__(self, lower, upper, lower_inclusive, upper_inclusive):
    self.lower = lower
    self.upper = upper
    self.lower_inclusive = lower_inclusive
    self.upper_inclusive = upper_inclusive

  @staticmethod
  def parse(version_range):
    first_char = version_range[0]
    last_index = len(version_range) - 1
    last_char = version_range[last_index]
    brackets_removed = version_range[1:last_index]
    range_split = brackets_removed.split(',')
    lower = range_split[0].strip()
    upper = range_split[1].strip()
    # print lower, upper, first_char == '[', last_char == ']'
    return VersionRange(lower, upper, first_char == '[', last_char == ']')


def populate_built_in_plugins(artifacts_dir):
  plugin_json_files = [pos_json for pos_json in os.listdir(artifacts_dir) if pos_json.endswith('.json')]

  for plugin_json_file in plugin_json_files:
    with open(os.path.join(artifacts_dir, plugin_json_file)) as f:
      return parse_plugin_json(f)


def populate_hub_plugins(hub_dir, cdap_version):
  packages_dir = os.path.join(hub_dir, "packages")
  # print "packages_dir", packages_dir
  for package_dir in os.listdir(packages_dir):
    # package_dir is a package name
    # print package_dir
    if os.path.isfile(os.path.join(packages_dir, package_dir)) or package_dir.startswith('.'):
      continue

    for version_dir in os.listdir(os.path.join(packages_dir, package_dir)):
      # version_dir is a version number of the package
      if os.path.isfile(os.path.join(packages_dir, package_dir, version_dir)) or version_dir.startswith('.'):
        continue

      if not is_valid_plugin(os.path.join(packages_dir, package_dir, version_dir, "spec.json"), cdap_version):
        # print 'not a valid plugin'
        continue

      # found a valid plugin. now parse its json file.
      plugin_json_file = get_plugin_json_file(os.path.join(packages_dir, package_dir, version_dir))
      print "market plugin json - ", plugin_json_file
      with open(plugin_json_file) as f:
        return parse_plugin_json(f)


def is_valid_plugin(package_spec_absolute_path, cdap_version):
  # print "checking valid plugin"
  with open(package_spec_absolute_path) as f:
    package_spec  = json.load(f)
    categories = package_spec['categories']
    # must be a plugin
    if not "hydrator-plugin" in categories:
      return False
    # must fall within version range, if such a range is defined
    if not 'cdapVersion' in package_spec:
      return True
    cdap_version_range = VersionRange.parse(package_spec['cdapVersion'])
    # print cdap_version_range.lower
    # print cdap_version_range.upper
    # print cdap_version_range.lower_inclusive
    # print cdap_version_range.upper_inclusive
    if LooseVersion(cdap_version_range.lower) < LooseVersion(cdap_version) < LooseVersion(cdap_version_range.upper):
      return True

    if cdap_version_range.lower_inclusive and LooseVersion(cdap_version_range.lower) == LooseVersion(cdap_version):
      return True

    if cdap_version_range.upper_inclusive and LooseVersion(cdap_version_range.upper) == LooseVersion(cdap_version):
      return True

    return False


def get_plugin_json_file(dir):
  json_files = [pos_json for pos_json in os.listdir(dir) if pos_json.endswith('.json') and pos_json != 'spec.json']
  return os.path.join(dir, json_files[0])


def parse_plugin_json(plugin_json_file):
  data = json.load(plugin_json_file)
  properties = data["properties"]
  for key in properties:
    # {
    #   "<plugin-name>": {
    #     "name": "<plugin-name>",
    #     "type": "<plugin-type>",
    #     "description": "<short description>",
    #     "icon": "<base64-encoded-icon>",
    #   }
    # }
    splits = key.split('.')
    config_type = splits[0]
    plugin_name_and_type = splits[1].split('-')
    plugin_name = plugin_name_and_type[0]
    plugin_type = plugin_name_and_type[1]
    parsed_plugins = {}

    # initialized plugin in result, if it is not already present
    if plugin_name not in parsed_plugins:
      parsed_plugins[plugin_name] = {}

    # add name, which will be overriden by display-name if available
    parsed_plugins[plugin_name]['name'] = plugin_name

    # add type
    parsed_plugins[plugin_name]['type'] = PLUGIN_DISPLAY_TYPES[plugin_type]

    if config_type == 'widgets':
      # add display name and icon
      add_display_name_and_icon(properties[key], parsed_plugins)
    elif config_type == 'doc':
      # add description
      add_description(properties[key], parsed_plugins)

    return parsed_plugins


def add_display_name_and_icon(widgets, dict_to_update):
  parsed_widgets = json.loads(widgets)
  if 'display-name' in parsed_widgets:
    dict_to_update['name'] = parsed_widgets['display-name']


def add_description(docs, dict_to_update):
  pass
  # print "desc"
  #print docs
  #print dict_to_update


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('cdap_sandbox_dir', help='Absolute path to the directory containing the CDAP Sandbox')
  parser.add_argument('hub_dir', help='Absolute path to the directory containing the Hub source')
  parser.add_argument('cdap_version', help='CDAP version to build plugin list for')
  args = parser.parse_args()

  artifacts_dir = os.path.join(args.cdap_sandbox_dir, 'artifacts')

  built_in_plugins = populate_built_in_plugins(artifacts_dir)
  print "########### built in #########"
  print built_in_plugins
  hub_plugins = populate_hub_plugins(args.hub_dir, args.cdap_version)
  print "########### hub #########"
  print hub_plugins

  # combine/union
  all_plugins = {}
  all_plugins.update(built_in_plugins)
  all_plugins.update(hub_plugins)


if __name__ == '__main__':
  main()
