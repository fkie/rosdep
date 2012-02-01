# Copyright (c) 2012, Willow Garage, Inc.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Willow Garage, Inc. nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import tempfile
import yaml

import rospkg.distro
import rosdep2.sources_list

def get_test_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), 'sources.list.d'))

def test_get_sources_list_dir():
    assert rosdep2.sources_list.get_sources_list_dir()

def test_get_sources_cache_dir():
    assert rosdep2.sources_list.get_sources_cache_dir()

def test_parse_sources_data():
    from rosdep2.sources_list import parse_sources_data
    
    parse_sources_data
    
def test_DataSource():
    from rosdep2.sources_list import DataSource
    data_source = DataSource('yaml', 'http://fake/url', ['tag1', 'tag2'])
    assert data_source == rosdep2.sources_list.DataSource('yaml', 'http://fake/url', ['tag1', 'tag2'])
    assert 'yaml' == data_source.type
    assert 'http://fake/url' == data_source.url
    assert ['tag1', 'tag2'] == data_source.tags
    assert 'yaml http://fake/url tag1 tag2' == str(data_source)

    data_source_foo = DataSource('yaml', 'http://fake/url', ['tag1', 'tag2'], origin='foo')
    assert data_source_foo != data_source
    assert data_source_foo.origin == 'foo'
    assert '[foo]:\nyaml http://fake/url tag1 tag2' == str(data_source_foo), str(data_source_foo)
    
    assert repr(data_source)

    try:
        rosdep2.sources_list.DataSource('yaml', 'http://fake/url', 'tag1', origin='foo')
        assert False, "should have raised"
    except ValueError:
        pass
    try:
        rosdep2.sources_list.DataSource('yaml', 'non url', ['tag1'], origin='foo')
        assert False, "should have raised"
    except ValueError:
        pass
    try:
        rosdep2.sources_list.DataSource('bad', 'http://fake/url', ['tag1'], origin='foo')
        assert False, "should have raised"
    except ValueError:
        pass
    try:
        rosdep2.sources_list.DataSource('yaml', 'http://host.no.path/', ['tag1'], origin='foo')
        assert False, "should have raised"
    except ValueError:
        pass

def test_parse_sources_file():
    from rosdep2.sources_list import parse_sources_file, InvalidSourcesFile
    for f in ['20-default.list', '30-nonexistent.list']:
        path = os.path.join(get_test_dir(), f)
        sources = parse_sources_file(path)
        assert len(sources) == 1
        assert sources[0].type == 'yaml'
        assert sources[0].origin == path, sources[0].origin
    try:
        sources = parse_sources_file('bad')
    except InvalidSourcesFile:
        pass
    
def test_parse_sources_list():
    from rosdep2.sources_list import parse_sources_list, InvalidSourcesFile
    path = get_test_dir()
    sources_list = parse_sources_list(sources_list_dir=get_test_dir())
    # at time test was written, at least two sources files
    assert len(sources_list) > 1
    # make sure files got loaded in intended order
    assert sources_list[0].origin.endswith('20-default.list')
    assert sources_list[1].origin.endswith('30-nonexistent.list')
    
    # tripwire -- we don't know what the actual return value is, but
    # should not error on a correctly configured test system.
    parse_sources_list()

def test_write_cache_file():
    from rosdep2.sources_list import write_cache_file, compute_filename_hash
    tempdir = tempfile.mkdtemp()
    
    filepath = write_cache_file(tempdir, 'foo', {'data': 1})
    computed_path = os.path.join(tempdir, compute_filename_hash('foo'))
    assert os.path.samefile(filepath, computed_path)
    with open(filepath, 'r') as f:
        assert {'data': 1} == yaml.load(f.read())
    
def test_update_sources_list():
    from rosdep2.sources_list import update_sources_list, InvalidSourcesFile, compute_filename_hash
    sources_list_dir=get_test_dir()
    tempdir = tempfile.mkdtemp()

    errors = []
    def error_handler(loc, e):
        errors.append((loc, e))
    retval = update_sources_list(sources_list_dir=sources_list_dir,
                                 sources_cache_dir=tempdir, error_handler=error_handler)
    assert retval
    assert len(retval) == 1, retval
    # one of our sources is intentionally bad, this should be a softfail
    assert len(errors) == 1, errors
    assert errors[0][0].url == 'https://badhostname.willowgarage.com/rosdep.yaml'

    source0, path0 = retval[0]
    assert source0.origin.endswith('20-default.list'), source0
    hash1 = compute_filename_hash(GITHUB_URL)
    hash2 = compute_filename_hash(BADHOSTNAME_URL)
    filepath = os.path.join(tempdir, hash1)
    assert filepath == path0, "%s vs %s"%(filepath, path0)
    with open(filepath, 'r') as f:
        data = yaml.load(f)
        assert 'python' in data

    # verify that cache index exists
    with open(os.path.join(tempdir, 'index'), 'r') as f:
        index = f.read().strip()
    expected = """#autogenerated by rosdep, do not edit. use 'rosdep update' instead
yaml %s 
yaml %s ubuntu"""%(hash1, hash2)
    assert expected == index, "\n[%s]\nvs\n[%s]"%(expected, index)

def test_load_cached_sources_list():
    from rosdep2.sources_list import load_cached_sources_list, update_sources_list
    tempdir = tempfile.mkdtemp()

    # test behavior on empty cache
    assert [] == load_cached_sources_list(sources_cache_dir=tempdir)
    
    # pull in cache data
    sources_list_dir=get_test_dir()
    retval = update_sources_list(sources_list_dir=sources_list_dir,
                                 sources_cache_dir=tempdir, error_handler=None)
    assert retval
    
    # now test with cached data
    retval = load_cached_sources_list(sources_cache_dir=tempdir)
    assert len(retval) == 2
    source0 = retval[0]
    source1 = retval[1]
    
    # this should be the 'default' source
    assert 'python' in source0.rosdep_data
    assert not source0.tags
    
    # this should be the 'non-existent' source
    assert source1.rosdep_data is None
    assert source1.tags == ['ubuntu']

def test_DataSourceMatcher():
    empty_data_source = rosdep2.sources_list.DataSource('yaml', 'http://fake/url', [])
    assert empty_data_source == rosdep2.sources_list.DataSource('yaml', 'http://fake/url', [])

    # matcher must match 'all' tags
    data_source = rosdep2.sources_list.DataSource('yaml', 'http://fake/url', ['tag1', 'tag2'])
    partial_data_source = rosdep2.sources_list.DataSource('yaml', 'http://fake/url', ['tag1'])

    # same tags as test data source
    matcher = rosdep2.sources_list.DataSourceMatcher(['tag1', 'tag2'])
    assert matcher.matches(data_source)
    assert matcher.matches(partial_data_source)
    assert matcher.matches(empty_data_source)

    # alter one tag
    matcher = rosdep2.sources_list.DataSourceMatcher(['tag1', 'tag3'])
    assert not matcher.matches(data_source)
    assert matcher.matches(empty_data_source)
    matcher = rosdep2.sources_list.DataSourceMatcher(['tag1'])
    assert not matcher.matches(data_source)

def test_download_rosdep_data():
    from rosdep2.sources_list import download_rosdep_data, SourceListDownloadFailure
    url = 'https://raw.github.com/ros/rosdep_rules/master/rosdep.yaml'
    data = download_rosdep_data(url)
    assert 'python' in data #sanity check

    # try with a bad URL
    try:
        data = download_rosdep_data('http://badhost.willowgarage.com/rosdep.yaml')
        assert False, "should have raised"
    except SourceListDownloadFailure as e:
        pass
    # try to trigger both non-dict clause and YAMLError clause
    for url in [
        'https://code.ros.org/svn/release/trunk/distros/',
        'https://code.ros.org/svn/release/trunk/distros/manifest.xml',
        ]:
        try:
            data = download_rosdep_data(url)
            assert False, "should have raised"
        except SourceListDownloadFailure as e:
            pass
    
BADHOSTNAME_URL = 'https://badhostname.willowgarage.com/rosdep.yaml'
GITHUB_URL = 'https://raw.github.com/ros/rosdep_rules/master/rosdep.yaml'
GITHUB_FUERTE_URL = 'https://raw.github.com/ros/rosdep_rules/master/rosdep_fuerte.yaml'
EXAMPLE_SOURCES_DATA_BAD_TYPE = "YAML %s"%(GITHUB_URL)
EXAMPLE_SOURCES_DATA_BAD_URL = "yaml not-a-url tag1 tag2"
EXAMPLE_SOURCES_DATA_BAD_LEN = "yaml"
EXAMPLE_SOURCES_DATA_NO_TAGS = "yaml %s"%(GITHUB_URL)
EXAMPLE_SOURCES_DATA = "yaml https://raw.github.com/ros/rosdep_rules/master/rosdep.yaml fuerte ubuntu"
EXAMPLE_SOURCES_DATA_MULTILINE = """
# this is a comment, above and below are empty lines

yaml %s
yaml %s fuerte ubuntu
"""%(GITHUB_URL, GITHUB_FUERTE_URL)
def test_parse_sources_data():
    from rosdep2.sources_list import parse_sources_data, TYPE_YAML, InvalidSourcesFile
    
    retval = parse_sources_data(EXAMPLE_SOURCES_DATA, origin='foo')
    assert len(retval) == 1
    sd = retval[0]
    assert sd.type == TYPE_YAML, sd.type
    assert sd.url == GITHUB_URL
    assert sd.tags == ['fuerte', 'ubuntu']
    assert sd.origin == 'foo'
    
    retval = parse_sources_data(EXAMPLE_SOURCES_DATA_NO_TAGS)
    assert len(retval) == 1
    sd = retval[0]
    assert sd.type == TYPE_YAML
    assert sd.url == GITHUB_URL
    assert sd.tags == []
    assert sd.origin == '<string>'

    retval = parse_sources_data(EXAMPLE_SOURCES_DATA_MULTILINE)
    assert len(retval) == 2
    sd = retval[0]
    assert sd.type == TYPE_YAML
    assert sd.url == GITHUB_URL
    assert sd.tags == []
    
    sd = retval[1]
    assert sd.type == TYPE_YAML
    assert sd.url == GITHUB_FUERTE_URL
    assert sd.tags == ['fuerte', 'ubuntu']
    
    for bad in [EXAMPLE_SOURCES_DATA_BAD_URL,
                EXAMPLE_SOURCES_DATA_BAD_TYPE,
                EXAMPLE_SOURCES_DATA_BAD_LEN]:
        try:
            parse_sources_data(bad)
            assert False, "should have raised: %s"%(bad)
        except InvalidSourcesFile as e:
            pass
        
def test_create_default_matcher():
    distro_name = rospkg.distro.current_distro_codename()
    os_detect = rospkg.os_detect.OsDetect()
    os_name, os_version, os_codename = os_detect.detect_os()

    matcher = rosdep2.sources_list.create_default_matcher()

    # matches full
    os_data_source = rosdep2.sources_list.DataSource('yaml', 'http://fake/url', [distro_name, os_name, os_codename])
    assert matcher.matches(os_data_source)

    # matches against current os
    os_data_source = rosdep2.sources_list.DataSource('yaml', 'http://fake/url', [os_name, os_codename])
    assert matcher.matches(os_data_source)
    
    # matches against current distro
    distro_data_source = rosdep2.sources_list.DataSource('yaml', 'http://fake/url', [distro_name])
    assert matcher.matches(distro_data_source)


def test_SourcesListLoader():
    from rosdep2.sources_list import SourcesListLoader
    loader = SourcesListLoader()
    
    assert [SourcesListLoader.RESOURCE_KEY] == loader.get_loadable_resources()    
    assert [SourcesListLoader.VIEW_KEY] == loader.get_loadable_views()
    assert SourcesListLoader.VIEW_KEY == loader.get_view_key(SourcesListLoader.RESOURCE_KEY)

    