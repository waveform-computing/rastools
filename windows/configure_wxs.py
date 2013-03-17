#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# vim: set et sw=4 sts=4:

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import io
import re
import sys
import subprocess
from xml.etree.ElementTree import fromstring, tostring, SubElement, _namespace_map


MY_PATH = os.path.dirname(__file__)
NAME = subprocess.check_output(['python', os.path.join(MY_PATH, '..', 'setup.py'), '--name']).strip()
VERSION = subprocess.check_output(['python', os.path.join(MY_PATH, '..', 'setup.py'), '--version']).strip()
sys.path.insert(0, os.path.join(MY_PATH, '..'))
from setup import ENTRY_POINTS, DESCRIPTION
# Set the WiX namespace as the default to prevent namespace prefixes in output
XMLNS = 'http://schemas.microsoft.com/wix/2006/wi'
_namespace_map[XMLNS] = ''


def configure_wxs(
        template=os.path.join(MY_PATH, 'template.wxs'),
        output=os.path.join(MY_PATH, NAME + '.wxs'),
        source_dir=os.path.join(MY_PATH, 'dist'),
        encoding='utf-8'):
    # Open the WiX installer template
    with io.open(template, 'rb') as f:
        document = fromstring(f.read().decode(encoding))
    product = document.find('{%s}Product' % XMLNS)
    product.attrib['Name'] = NAME
    product.attrib['Version'] = VERSION
    package = product.find('./{%s}Package' % XMLNS)
    package.attrib['Description'] = DESCRIPTION
    # Construct Component/File elements for all files under source_dir
    # (ignoring any entries that are already present)
    install_dir = product.find('.//{%s}Directory[@Id="INSTALLDIR"]' % XMLNS)
    install_dir.attrib['FileSource'] = source_dir
    add_components(source_dir, install_dir)
    # Add all console_script entry points to the CLIFeature
    root_feature = product.find('./{%s}Feature[@Id="RootFeature"]' % XMLNS)
    cli_feature = root_feature.find('./{%s}Feature[@Id="CLIFeature"]' % XMLNS)
    if cli_feature is None:
        cli_feature = SubElement(root_feature, '{%s}Feature' % XMLNS)
        cli_feature.attrib['Id'] = 'CLIFeature'
        cli_feature.attrib['Title'] = 'Command line applications'
    add_cli_scripts(product, install_dir, cli_feature)
    # Add all gui_script entry_points to the GUIFeature and configure their icons
    gui_feature = root_feature.find('./{%s}Feature[@Id="GUIFeature"]' % XMLNS)
    if gui_feature is None:
        gui_feature = SubElement(root_feature, '{%s}Feature' % XMLNS)
        gui_feature.attrib['Id'] = 'GUIFeature'
        gui_feature.attrib['Title'] = 'Graphical applications'
    add_gui_scripts(product, install_dir, gui_feature)
    # Fix up name substitutions because WiX/MSI is horribly inconsistent in
    # where it permits substitutions...
    install_dir.attrib['Name'] = NAME
    menu_dir = product.find('.//{%s}Directory[@Id="ProgramMenuDir"]' % XMLNS)
    menu_dir.attrib['Name'] = NAME
    root_feature = product.find('./{%s}Feature[@Id="RootFeature"]' % XMLNS)
    root_feature.attrib['Title'] = NAME
    # Find the default <Feature> element or create one if it doesn't exist
    default_feature = product.find('.//{%s}Feature[@Id="DefaultFeature"]' % XMLNS)
    all_features = product.findall('.//{%s}Feature' % XMLNS)
    if default_feature is None:
        default_feature = SubElement(product, '{%s}Feature' % XMLNS)
        default_feature.attrib['Id'] = 'DefaultFeature'
        default_feature.attrib['Title'] = 'Default Feature'
    # Add all created components to the default feature, unless they're already
    # present in that (or any other) feature
    for comp_elem in product.findall('.//{%s}Component' % XMLNS):
        ref_id = get_component_id(comp_elem)
        comp_ref = None
        for feature in all_features:
            comp_ref = feature.find('./{%s}ComponentRef[@Id="%s"]' % (XMLNS, ref_id))
            if comp_ref is not None:
                break
        if comp_ref is None:
            SubElement(default_feature, 'ComponentRef').attrib['Id'] = ref_id
    indent(document)
    with io.open(output, 'wb') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write(tostring(document, encoding=encoding))


def add_components(path, dir_elem):
    for name in os.listdir(path):
        fullname = os.path.join(path, name)
        if os.path.isfile(fullname):
            file_elem = dir_elem.find('./{%s}Component/{%s}File[@Name="%s"]' % (XMLNS, XMLNS, name))
            if file_elem is None:
                comp_elem = SubElement(dir_elem, '{%s}Component' % XMLNS)
                file_elem = SubElement(comp_elem, '{%s}File' % XMLNS)
                file_elem.attrib['Name'] = name
            file_elem.attrib['Id'] = get_path_id(fullname)
            file_elem.attrib['KeyPath'] = 'yes'
        elif os.path.isdir(fullname):
            child_elem = dir_elem.find('./{%s}Directory[@Name="%s"]' % (XMLNS, name))
            if child_elem is None:
                child_elem = SubElement(dir_elem, '{%s}Directory' % XMLNS)
                child_elem.attrib['Id'] = get_path_id(fullname)
                child_elem.attrib['Name'] = name
            add_components(fullname, child_elem)


def add_cli_scripts(product_elem, dir_elem, feature_elem):
    scripts = [
        ep.split('=')[0].rstrip()
        for ep in ENTRY_POINTS['console_scripts']
        ]
    all_components = dir_elem.findall('./{%s}Component' % XMLNS)
    cli_components = [
        (script, component)
        for component in all_components
        for script in scripts
        if component.find('./{%s}File[@Name="%s.exe"]' % (XMLNS, script)) is not None
        ]
    for (script, component) in cli_components:
        if 'Id' not in component.attrib:
            component.attrib['Id'] = '%s.exe' % script
        SubElement(feature_elem, '{%s}ComponentRef' % XMLNS).attrib['Id'] = component.attrib['Id']


def add_gui_scripts(product_elem, dir_elem, feature_elem):
    shortcuts = SubElement(feature_elem, '{%s}ComponentRef' % XMLNS)
    shortcuts.attrib['Id'] = 'StartMenuShortcuts'
    scripts = [
        ep.split('=')[0].rstrip()
        for ep in ENTRY_POINTS['gui_scripts']
        ]
    all_component_elems = dir_elem.findall('./{%s}Component' % XMLNS)
    gui_component_elems = [
        (script, component_elem)
        for component_elem in all_component_elems
        for script in scripts
        if component_elem.find('./{%s}File[@Name="%s.exe"]' % (XMLNS, script)) is not None
        ]
    for (script, component_elem) in gui_component_elems:
        if 'Id' not in component_elem.attrib:
            component_elem.attrib['Id'] = '%s.exe' % script
        file_elem = component_elem.find('./{%s}File[@Name="%s.exe"]' % (XMLNS, script))
        add_shortcut(product_elem, dir_elem, file_elem, script, 'DesktopFolder')
        add_shortcut(product_elem, dir_elem, file_elem, script, 'ProgramMenuDir')
        SubElement(feature_elem, '{%s}ComponentRef' % XMLNS).attrib['Id'] = component_elem.attrib['Id']


def add_shortcut(product_elem, dir_elem, file_elem, script, folder):
    shortcut_elem = file_elem.find('./{%s}Shortcut[@Directory="%s"]' % (XMLNS, folder))
    if shortcut_elem is None:
        shortcut_elem = SubElement(file_elem, '{%s}Shortcut' % XMLNS)
        shortcut_elem.attrib['Directory'] = folder
    shortcut_elem.attrib['Id'] = '%s_%s' % (folder, script)
    shortcut_elem.attrib['Name'] = script
    shortcut_elem.attrib['Advertise'] = 'yes'
    shortcut_elem.attrib['Icon'] = '%s_%s.exe' % (folder, script)
    shortcut_elem.attrib['IconIndex'] = '0'
    add_icon(product_elem, shortcut_elem.attrib['Icon'], os.path.join(
        dir_elem.attrib['FileSource'], '%s.exe' % script))


def add_icon(product_elem, icon_id, source_file):
    icon_elem = product_elem.find('./{%s}Icon[@Id="%s"]' % (XMLNS, icon_id))
    if icon_elem is None:
        icon_elem = SubElement(product_elem, '{%s}Icon' % XMLNS)
        icon_elem.attrib['Id'] = icon_id
    icon_elem.attrib['SourceFile'] = source_file


def get_component_id(comp_elem):
    try:
        return comp_elem.attrib['Id']
    except KeyError:
        pass
    file_elem = comp_elem.find('./{%s}File[@KeyPath="yes"]' % XMLNS)
    if file_elem is not None:
        try:
            return file_elem.attrib['Id']
        except KeyError:
            try:
                return file_elem.attrib['Name']
            except KeyError:
                pass
    raise ValueError(
        'Unable to determine Id of <Component> from its children: %s' % tostring(comp_elem))


_path_ids = {}
_used_ids = set()
def get_path_id(path):
    global _path_ids
    try:
        return _path_ids[path]
    except KeyError:
        path_id = re.sub(r'[^a-zA-Z0-9_.]', '_', path)
        if path_id in _used_ids:
            suffix = 2
            while '%s%d' % (path_id, suffix) in _used_ids:
                suffix += 1
            path_id = '%s%d' % (path_id, suffix)
        _path_ids[path] = path_id
        _used_ids.add(path_id)
        return path_id


def indent(elem, level=0, indent_str='  '):
    i = '\n' + indent_str * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + indent_str
        for child in elem:
            indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = i
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


if __name__ == '__main__':
    configure_wxs(sys.argv[1], sys.argv[2])
