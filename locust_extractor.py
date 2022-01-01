"""Sample script to extract flows on MITMProxy into usable locust load test scripts.

Each destination will generate a corresponding test file.
"""
import argparse
import re
from textwrap import dedent
from six.moves.urllib.parse import quote, quote_plus
import sys

# import json
# import base64
# import zlib
import os
import typing  # noqa

# from datetime import datetime
# from datetime import timezone

import mitmproxy

from mitmproxy import command
from mitmproxy import connection  # noqa
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import version
from mitmproxy.utils import strutils
from mitmproxy.net.http import cookies

import pyperclip


class locust(object):
    """Locust code generator."""

    __hosts_list__ = None
    __locusts__ = {}

    def __init__(self) -> None:
        """Init code generator per destination host."""
        self.__locusts__ = {}
        return

    def locust_code(self, flow: flow.Flow) -> str:
        """Generate main locust code."""
        code = dedent("""
            # -*- coding: UTF-8 -*-

            from locust import HttpUser, SequentialTaskSet, task, between
            from operator import attrgetter
            import gevent


            class UserBehavior(SequentialTaskSet):
            
                @task()
                def {name}(self):
                    url = '{url}'
                    {headers}{params}{data}
                    self.response = self.client.request(
                        method='{method}',
                        url=url,{args}
                    )

                ### Additional tasks can go here ###


            class WebsiteUser(HttpUser):
                tasks = [UserBehavior]
                wait_time = between(1,3)
                """).strip()
        components = [quote(x, safe="") for x in flow.request.path_components]
        file_name = "_".join(components)
        name = re.sub(r'\W|^(?=\d)', '_', file_name)
        url = flow.request.scheme + "://" + flow.request.host + "/" + "/".join(
            components)
        if name == "" or name is None:
            new_name = str(flow.request.host)
            name = re.sub(r'\W|^(?=\d)', '_', new_name)
        name = 'task_{:06d}_'.format(flow.count) + "_".join(
            [str(flow.request.method), name])
        name = name.replace('__', '_')
        args = ""
        headers = ""
        if flow.request.headers:
            lines = [
                "            '{}': '{}',\n".format(
                    k.decode('utf-8'), v.decode('utf-8'))
                for k, v in flow.request.headers.fields
                if k.decode('utf-8').lower() not in ["host", "cookie"]
            ]
            headers += "\n        headers = {{\n{}        }}\n".format(
                "".join(lines))
            args += "\n            headers=headers,"
        params = ""
        if flow.request.query:
            lines = [
                "            '{}': '{}',\n".format(k, v)
                for k, v in flow.request.query.items()
            ]
            params = "\n        params = {{\n{}        }}\n".format(
                "".join(lines))
            args += "\n            params=params,"
        data = ""
        if flow.request.content:
            data = "\n        data = '''{}'''\n".format(flow.request.content)
            args += "\n            data=data,"
        code = code.format(
            name=name,
            url=url,
            headers=headers,
            params=params,
            data=data,
            method=flow.request.method,
            args=args,
        )
        host = flow.request.scheme + "://" + flow.request.host
        code = code.replace(host, "' + self.user.host + '")
        code = code.replace(
            quote_plus(host), "' + quote_plus(self.user.host) + '")
        code = code.replace(quote(host), "' + quote(self.user.host) + '")
        code = code.replace("'' + ", "")
        code = code.replace("'''b'", "'''")
        code = code.replace("''''", "'''")
        return code

    def locust_task(self, flow: flow.Flow) -> str:
        "Generate locust task."
        code = self.locust_code(flow)
        start_task = len(code.split('@task')[0]) - 4
        end_task = -19 - len(code.split('### Additional')[1])
        task_code = code[start_task:end_task]
        return task_code

    def add(self, host: str, flow: flow.Flow) -> None:
        """Add hosts per/for a flow."""
        if host not in list(self.__locusts__.keys()):
            self.__locusts__[host] = self.locust_code(flow)
        else:
            insertion_index = self.__locusts__[host].find('class WebsiteUser') 
            tmp = self.__locusts__[host][:insertion_index]
            tmp += self.locust_task(flow)
            tmp += '\n'
            tmp += self.__locusts__[host][insertion_index:]
            self.__locusts__[host] = tmp
        return

    def get(self, host: str) -> str:
        """Return flow for a given host."""
        return self.__locusts__[host]


global context
# context = locust()


class ExtractLocust(object):

    def __init__(self) -> None:
        """Init locust.replay extractor."""
        # Initialize data collection
        self.context = locust()
        self.context.hosts_list = set()
        self.context.locusts = locust()
        self.context.count = 0
        self.context.dump_file = None


    def load(self, loader) -> None:
        """Define options passed to this add-on."""
        loader.add_option(
            name = "filename_prefix",
            typespec = str,
            default = "test",
            help = "Filename will be prepended to the discovered destination host, default prefix is 'test'.",
        )


    def configure(self, _) -> None:
        """Keep configuration options in context."""
        self.context.dump_file = ctx.options.filename_prefix
        ctx.log.info('Dump file prefix "{}"'.format(repr(self.context.dump_file)))


    def request(self, flow: flow.Flow) -> None:
        """Get a flow from MITMProxy."""
        flow.count = self.context.count
        self.context.count += 1
        self.context.hosts_list.add(flow.request.host)
        self.context.locusts.add(flow.request.host, flow)


    @command.command("locust.task.clip")
    def task_clip(self, flows: typing.Sequence[flow.Flow]) -> None:
        """Export a flow to the system clipboard as locust task."""
        ctx.log.info(str(type(flows)))
        data = ''
        for f in flows:
            v = strutils.always_str(self.context.locust_task(f))
            data += v
        try:
            pyperclip.copy(data)
        except pyperclip.PyperclipException as e:
            ctx.log.error(str(e))


    @command.command("locust.code.clip")
    def code_clip(self, flows: typing.Sequence[flow.Flow]) -> None:
        """Export a flow to the system clipboard as locust code."""
        ctx.log.info(str(type(flows)))
        data = strutils.always_str(self.context.locust_code(flows[0]))
        if len(flows)>1:
            for f in flows[1:]:
                v = strutils.always_str(self.context.locust_task(f))
                tmp = data[:-100]
                tmp += v + '\n'
                tmp += data[-100:]
                data = tmp
        try:
            pyperclip.copy(data)
        except pyperclip.PyperclipException as e:
            ctx.log.error(str(e))


    @command.command("locust.extractAll")
    def done(self) -> None:
        """Save all extracted flows when MITMProxy exits."""
        for host in self.context.hosts_list:
            hostfile = re.sub(r'\W|^(?=\d)', '_', host)
            filename = self.context.dump_file + '-' + hostfile + '.py'
            code = self.context.locusts.get(host)
            open(filename, "w").write(code)


addons = [
    ExtractLocust()
]
