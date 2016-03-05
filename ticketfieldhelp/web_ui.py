# vim: sts=4 sw=4

from pkg_resources import resource_filename

from trac.core import Component, implements
from trac.web.api import IRequestFilter, ITemplateStreamFilter, IRequestHandler
from trac.web.chrome import (ITemplateProvider,
                             add_script, add_stylesheet)
from trac.cache import cached

from genshi.builder import tag
from genshi.filters.transform import Transformer

import json
from trac.wiki.model import WikiPage
from trac.wiki.formatter import format_to_html
from trac.mimeview.api import Context

from trac.env import open_environment
import os.path


class TicketFieldHelpPlugin (Component):
    implements(IRequestHandler,
            IRequestFilter,
            ITemplateStreamFilter,
            ITemplateProvider)

    @cached
    def _fields (self):
        fields = {}
        for key, value in self.env.config['ticket-field-help'].options():
            if value.startswith('wiki:'):
                schema, value = [e.strip() for e in value.split(':', 1)]
            else:
                schema = 'text'
            fields[key] = (schema, value)
        return fields


    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        yield 'ticketfieldhelp', resource_filename(__name__, 'htdocs')

    def get_templates_dirs(self):
        return []

    # IRequestFilter
    def pre_process_request (self, req, handler):
        return handler

    def post_process_request (self, req, template, data, content_type):
        if req.path_info.startswith('/newticket') or\
           req.path_info.startswith('/ticket/'):
            add_script(req, 'ticketfieldhelp/js/jquery.tooltipster.min.js')
            add_stylesheet(req, 'ticketfieldhelp/css/tooltipster.css')
            add_stylesheet(req, 'ticketfieldhelp/css/themes/tooltipster-shadow.css')
        return template, data, content_type

    # ITemplateStreamFilter methods
    def filter_stream (self, req, method, filename, stream, data):
        if not req.path_info.startswith('/newticket') and\
           not req.path_info.startswith('/ticket/'):
            return stream

        if len(self._fields) == 0:
            return stream

        for k,v in self._fields.items():
            xpath = '//label[@for="field-' + k + '"]'
            schema, v = v
            if schema == 'wiki':
                stream |= Transformer(xpath)\
                            .attr('class', 'tfhelp tfhelp-wiki')
            else:
                stream |= Transformer(xpath)\
                            .attr('class', 'tfhelp tfhelp-text')\
                            .attr('title', v)

        stream |= Transformer('//head').append(tag.script('''
(function($) {
    $(function() {
        $.fn.tooltipster('setDefaults', {
            theme: 'tooltipster-shadow',
            trigger: 'click',
            delay: 100,
        });
        $('label.tfhelp').css('cursor','help');
        $('label.tfhelp-text').tooltipster();
        $('label.tfhelp-wiki').tooltipster({
            content: 'Loading...',
            functionBefore: function(origin, continueTooltip) {
                if (origin.data('ajax') == 'cached') {
                    continueTooltip();
                }
                else {
                    # FIXME loading large contents breaks tooltip.
                    # we can't call continueTooltip() here.
                    field = origin.attr('for').replace('field-', '');
                    $.ajax({
                        type: 'GET',
                        url: '%s/ticket-field-help/' + field,
                        success: function(data) {
                            dom = $(data.content);
                            origin.tooltipster('content', dom).data('ajax', 'cached');
                            continueTooltip();
                        },
                    });
                }
            }
        });
    });
})(jQuery);
            ''' % req.base_url, type='text/javascript'))

        return stream


    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info.startswith('/ticket-field-help/')

    def process_request(self, req):
        field_name = req.path_info.split('/', 2)[-1]
        data = { 'name': field_name }

        if field_name in self._fields:
            schema, value = self._fields[field_name]
            content = self._get_wiki_content(req, value)
        else:
            content = 'Invalid field name'

        data['content'] = content
        req.send(json.dumps(data).encode('utf-8'), 'application/json')

    @cached
    def _intertracs (self):
        # FIXME this assumes trac envs are arranged under the same directory
        intertracs = {}
        aliases = {}
        for key, value in self.env.config['intertrac'].options():
            if key.endswith('.url'):
                intertracs[key.split('.')[0]] = os.path.basename(value)
            else:
                aliases[key] = value
        for alias, to in aliases.items():
            if to in intertracs:
                intertracs[alias] = intertracs[to]
        return intertracs

    def _get_wiki_content (self, req, value):
        elts = value.split(':', 1)
        if len(elts) == 1 or elts[0] not in self._intertracs:
            env = self.env
            page_name = value
        else:
            path = os.path.join(os.path.dirname(self.env.path), elts[0])
            env = open_environment(path, True)
            page_name = elts[-1]

        page = WikiPage(env, page_name)
        if not page.exists:
            return 'No page'
        context = Context.from_request(req)
        return format_to_html(env, context, page.text)
