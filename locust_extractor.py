"""Sample script to extract flows on mitmproxy into usable locust load test scripts.

   Each destination will generate a corresponding test file.
"""
import re
from textwrap import dedent
from six.moves.urllib.parse import quote, quote_plus
import sys


class locust(object):
    __hosts_list__ = None
    __locusts__ = dict()

    def __init__(self):
        self.__locusts__ = dict()
        return

    def __locust_code(self, flow):
        code = dedent("""
            from locust import HttpLocust, TaskSet, task
            from operator import attrgetter
            import time

            class UserBehavior(TaskSet):
                def on_start(self):
                    ''' on_start is called when a Locust start before any task is scheduled.
                        Here we sort the tasks by name. '''
                    ns = attrgetter('__name__')
                    self.tasks = sorted(self.tasks, key=ns)
                    self.next_task_nr = 0
                    time.sleep(1)

                def get_next_task(self):
                    next_task = self.tasks[self.next_task_nr]
                    self.next_task_nr = (self.next_task_nr + 1) % len(self.tasks)
                    return next_task

                @task()
                def {name}(self):
                    url = '{url}'
                    {headers}{params}{data}
                    self.response = self.client.request(
                        method='{method}',
                        url=url,{args}
                    )

                ### Additional tasks can go here ###


            class WebsiteUser(HttpLocust):
                task_set = UserBehavior
                min_wait = 1000
                max_wait = 3000
                """).strip()
        components = map(lambda x: quote(x, safe=""), flow.request.path_components)
        file_name = "_".join(components)
        name = re.sub('\W|^(?=\d)', '_', file_name)
        url = flow.request.scheme + "://" + flow.request.host + "/" + "/".join(components)
        if name == "" or name is None:
            new_name = str(flow.request.host)
            name = re.sub('\W|^(?=\d)', '_', new_name)
        name = 'task_{:06d}_'.format(flow.count) + "_".join([str(flow.request.method), name])
        name = name.replace('__', '_')
        args = ""
        headers = ""
        if flow.request.headers:
            lines = ["            '%s': '%s',\n" % (k, v) for k, v in flow.request.headers.fields if k.lower() not in ["host", "cookie"]]
            headers += "\n        headers = {\n%s        }\n" % "".join(lines)
            args += "\n            headers=headers,"
        params = ""
        if flow.request.query:
            lines = ["            '%s': '%s',\n" % (k, v) for k, v in flow.request.query.collect()]
            params = "\n        params = {\n%s        }\n" % "".join(lines)
            args += "\n            params=params,"
        data = ""
        if flow.request.body:
            data = "\n        data = '''%s'''\n" % flow.request.body
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
        code = code.replace(host, "' + self.locust.host + '")
        code = code.replace(quote_plus(host), "' + quote_plus(self.locust.host) + '")
        code = code.replace(quote(host), "' + quote(self.locust.host) + '")
        code = code.replace("'' + ", "")
        return code

    def __locust_task(self, flow):
        code = self.__locust_code(flow)
        start_task = len(code.split('@task')[0]) - 4
        end_task = -19 - len(code.split('### Additional')[1])
        task_code = code[start_task:end_task]
        return task_code

    def add(self, host, flow):
        if host not in self.__locusts__.keys():
            self.__locusts__[host] = self.__locust_code(flow)
        else:
            tmp = self.__locusts__[host][:-100]
            tmp += self.__locust_task(flow)
            tmp += '\n'
            tmp += self.__locusts__[host][-100:]
            self.__locusts__[host] = tmp
        return

    def get(self, host):
        return self.__locusts__[host]

global context
context = locust()


def start():
    context.dump_file = None
    if len(sys.argv) > 1:
        context.dump_file = sys.argv[1]
    else:
        raise ValueError(
            'Usage: -s "locust_extractor.py filename" '
            '(where filename will be prepended to the discovered destination host)'
        )
    context.hosts_list = set()
    context.locusts = locust()
    context.count = 0


def request(flow):
    flow.count = context.count
    context.count += 1
    context.hosts_list.add(flow.request.host)
    context.locusts.add(flow.request.host, flow)


def done():
    for host in context.hosts_list:
        hostfile = re.sub('\W|^(?=\d)', '_', host)
        filename = context.dump_file + '-' + hostfile + '.py'
        code = context.locusts.get(host)
        file(filename, "w").write(code)
