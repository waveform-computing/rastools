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
import uuid
from xml.etree.ElementTree import fromstring, tostring, SubElement, _namespace_map


# Find the various paths
MY_PATH = os.path.dirname(__file__)
PROJECT_PATH = os.path.dirname(MY_PATH)

# Set the WiX namespace as the default to prevent namespace prefixes in output
XMLNS = 'http://schemas.microsoft.com/wix/2006/wi'
_namespace_map[XMLNS] = ''


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


def configure_wxs(
        template=os.path.join(MY_PATH, 'template.wxs'),
        output=os.path.join(PROJECT_PATH, 'rastools.wxs'),
        source_dir=os.path.join(PROJECT_PATH, 'dist'),
        encoding='utf-8'):
    # Open the WiX installer template
    with io.open(template, 'rb') as f:
        document = fromstring(f.read().decode(encoding))
    # Replace Product[@Id] to force "major upgrade" semantics
    product = document.find('{%s}Product' % XMLNS)
    product.attrib['Id'] = str(uuid.uuid1()).upper()
    # XXX Fix Manufacturer, Name, and Version attributes
    # Construct Component/File elements for all files under source_dir
    # (ignoring any entries that are already present)
    install_dir = product.find('.//{%s}Directory[@Id="INSTALLDIR"]' % XMLNS)
    install_dir.attrib['FileSource'] = source_dir
    add_components(source_dir, install_dir)
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


if __name__ == '__main__':
    configure_wxs(sys.argv[1], sys.argv[2])
