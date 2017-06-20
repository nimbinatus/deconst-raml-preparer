#! usr/bin/env python3

from bs4 import BeautifulSoup
import json
import subprocess
import os
import urllib
from pathlib import Path

import ramlpreparer.builders.asset_mapper as asset_mapper
import ramlpreparer.builders.common as common
import ramlpreparer.builders.tocbuilder as tocbuilder
import ramlpreparer.builders.raml2html as raml2html
from ramlpreparer.config import Configuration

# Initialize the raml2html package.
starter_call = os.path.join(
    os.getcwd(), 'ramlpreparer', 'scripts', 'npminstall.sh')
subprocess.call(starter_call, shell=True)


class Envelope_RAML:
    '''
    A class for metadata envelopes. The docname variable should be the basename
    of the RAML file.
    '''

    def __init__(self, docname, body, originalFile=None, title=None, toc=None,
                 publish_date=None, unsearchable=None, content_id=None,
                 meta=None, asset_offsets=None, addenda=None,
                 deconst_config=None, per_page_meta=None,
                 github_edit_url=None):
        '''
        Run populations
        '''
        self.docname = docname
        self.body = body
        self.originalFile = originalFile
        self.title = title
        self.toc = toc
        self.publish_date = publish_date
        self.addenda = addenda
        self.unsearchable = unsearchable
        if per_page_meta:
            self.per_page_meta = per_page_meta
        else:
            self.per_page_meta = {}

        if not deconst_config:
            self._populate_deconst_config()
        else:
            self.deconst_config = deconst_config

        if not content_id:
            self._populate_content_id()
        else:
            self.content_id = content_id

        if not meta:
            self._populate_meta()
        else:
            self.meta = meta

        if not asset_offsets:
            self._populate_asset_offsets()
        else:
            self.asset_offsets = asset_offsets

        # self._populate_unsearchable()
        if not github_edit_url:
            self._populate_git()
        else:
            self.github_edit_url = github_edit_url

    def make_an_envelope(self):
        '''
        Make an envelope!
        '''
        the_envelope = {
            'body': self.body,
            'docname': self.docname,
            'title': self.title,
            'toc': self.toc,
            'unsearchable': self.unsearchable,
            'content_id': self.content_id,
            'meta': self.meta,
            'asset_offsets': self.asset_offsets,
            'addenda': self.addenda,
            'per_page_meta': self.per_page_meta
        }
        return the_envelope

    def serialization_path(self, test=False):
        '''
        Generate the full path at which this envelope should be serialized.
        '''
        envelope_filename = urllib.parse.quote(
            self.content_id, safe='') + '.json'
        if test == False:
            return os.path.join(self.deconst_config['envelope_dir'], envelope_filename)
        else:
            return os.path.join(self.deconst_config.envelope_dir, envelope_filename)

    def _populate_meta(self, test=False):
        '''
        Merge repository-global and per-page metadata into the envelope's
        metadata.
        '''
        if test == True:
            self.meta = self.deconst_config['meta'].copy()
        else:
            self.meta = self.deconst_config.meta.copy()
        self.meta.update(self.per_page_meta)

    def _populate_git(self, test=False):
        '''
        Set the github_edit_url property within "meta".
        '''
        if test == True:
            if self.deconst_config['git_root'] and self.deconst_config['github_url']:
                git_root_path = self.deconst_config['git_root']
            else:
                git_root_path = os.getcwd()
            for (dirpath, dirnames, filenames) in os.walk(git_root_path):
                for filename in filenames:
                    if filename.endswith(str(self.docname)):
                        for dirname in dirnames:
                            actual_path = str(
                                Path(dirname).parents[0])[:-2]
                            full_path = os.path.join(
                                dirpath, actual_path, filename)
            edit_segments = [self.deconst_config['github_url'], 'edit',
                             self.deconst_config['github_branch'],
                             os.path.relpath(full_path, start='.')]
            stripped_segments = []
            for segment in edit_segments:
                stripped_segments.append(segment.strip('/'))
            self.meta['github_edit_url'] = (
                '/'.join(segment for segment in stripped_segments))
        else:
            base_name = os.path.basename(self.docname)
            if self.deconst_config.git_root and self.deconst_config.github_url:
                git_root_path = self.deconst_config.git_root
            elif self.deconst_config.github_url and not self.deconst_config.git_root:
                git_root_path = getcwd()
            for (dirpath, dirnames, filenames) in os.walk(git_root_path):
                for filename in filenames:
                    if filename.endswith(base_name):
                        for dirname in dirnames:
                            actual_path = str(
                                Path(dirname).parents[0])[:-2]
                            full_path = os.path.join(
                                dirpath, actual_path, filename)
            edit_segments = [self.deconst_config.github_url, 'edit',
                             self.deconst_config.github_branch,
                             os.path.relpath(full_path, start='.')]
            stripped_segments = []
            for segment in edit_segments:
                stripped_segments.append(segment.strip('/'))
            self.meta['github_edit_url'] = (
                '/'.join(segment for segment in stripped_segments))

    # TODO: Add an unsearchable feature.
    # def _populate_unsearchable(self):
    #     '''
    #     Populate "unsearchable" from per-page or repository-wide settings.
    #     '''
    #     unsearchable = self.per_page_meta.get(
    #         'deconstunsearchable', self.config.deconst_default_unsearchable)
    #     if unsearchable is not None:
    #         self.unsearchable = unsearchable in ('true', True)

    def _populate_asset_offsets(self, original_asset_dir=None):
        '''
        Read stored asset offsets from the asset mapper, and then update the body.
        '''
        if original_asset_dir:
            classy = Configuration(os.environ)
            self.body, self.asset_offsets = asset_mapper.map_the_assets(
                original_asset_dir, classy.asset_dir, html_doc_path=self.originalFile)
        else:
            classy = Configuration(os.environ)
            self.body, self.asset_offsets = asset_mapper.map_the_assets(
                classy.original_asset_dir, classy.asset_dir, html_doc_path=self.originalFile)

    def _populate_content_id(self, testing=False):
        '''
        Derive this envelope's content ID.
        '''
        self.content_id = common.derive_content_id(
            self.deconst_config, self.docname, test=testing)

    def _populate_deconst_config(self):
        '''
        Pull in all the deconst json info
        '''
        self.deconst_config = common.init_builder()


def make_it_html(raml, output_html):
    '''
    Takes in the RAML and gives out HTML
    '''
    raml2html.raml2html(raml, output_html)
    return output_html


def parsing_html(page, page_title=None):
    '''
    Parse the HTML to put it in an envelope. Optional arguments are for
    unittests only.
    '''
    try:
        with open(page, 'r') as contents:
            soupit = BeautifulSoup(contents, 'html.parser')
        with open(page, 'r') as contents2:
            that_page = tocbuilder.parse_it(contents2)
    except OSError:
        soupit = BeautifulSoup(page, 'html.parser')
        that_page = tocbuilder.parse_it(page)
    toc_html = tocbuilder.htmlify(that_page)
    if page_title == None:
        the_title = soupit.title.string
    else:
        the_title = page_title
    set_up_class = Envelope_RAML(page,
                                 soupit.body,
                                 originalFile=page,
                                 title=the_title,
                                 toc=toc_html)
    whole_envelope = set_up_class.make_an_envelope()
    return whole_envelope


def write_out(envelope, file_path=None):
    '''
    Write the HTML out as JSON to the serialized path. An
    error is raised if you don't have a file path or an envelope.
    '''
    if file_path is None:
        file_path = envelope.serialization_path()
    with open(file_path, 'w') as thefile:
        json.dump(envelope, thefile)
    return thefile


# QUESTION: Does each page's envelope need to get placed separately? Currently,
# it's written to put each envelope inside of a larger envelope...
# DONE: Write each envelope to a new file in ENVELOPE_DIR.
# DONE: Review the code from the Sphinx preparer if anything should be copied.
