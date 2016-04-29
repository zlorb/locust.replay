# Locust.Replay

[Locust.io](http://locust.io "http://locust.io") is an easy-to-use, distributed, user load testing tool. Intended for load testing web sites or APIs and figuring out how many concurrent users a system can handle.

Sometimes, one needs to get basic load test up and running quickly, for a non-trivial set of interactions. One possible approach could be recording a session with the system under test and the replay it at higher loads.

This is where [mitmproxy](https://mitmproxy.org "https://mitmproxy.org") comes into play. **mitmproxy** is an interactive console program that allows traffic flows to be intercepted, inspected, modified and replayed.

**mitmproxy** developers have been generous to allow my pull-request, which lets users export flows captured to locust script format. This way a test session that involves multiple interactions can be developed within minutes.

Following is a simple example, that explains this concept.

## Getting Started

Obviously, **mitmproxy** and **locust** have to be installed. **mitmproxy** version >=0.18 or latest
github code is required. Please follow the corresponding user manuals for each. It is also beyond the scope of this document to explain basic usage for these tools. However, basic steps are:

* Run mitmproxy, for example:

  ```mitmproxy --anticache```

* Configure a client (such as a browser) to use it as a proxy, if needed.
* Perform the manual test session, simulating a single user. In this example we will search the web.

## Export to Code
* On mitmproxy console, select the first flow, i.e., the flow that should initialize each user session. Then press the **E** key, which is a shortcut for *Export* and then press **l**, for *locust code*.

![mitmproxy console](https://raw.githubusercontent.com/zlorb/locust.replay/master/images/mitmproxy_screenshot.png "mitmproxy console")

* The code will be placed in your clipboard. Pasting it to your favorite editor will result in something like:

```python
from locust import HttpLocust, TaskSet, task

class UserBehavior(TaskSet):
    def on_start(self):
        ''' on_start is called when a Locust start before any task is scheduled '''
        self.www_google_com_1461888928_75()

    @task()
    def www_google_com_1461888928_75(self):
        url = self.locust.host + '/'

        headers = {
            ':method': 'GET',
            ':path': '/',
            ':authority': 'www.google.com',
            ':scheme': 'https',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:46.0) Gecko/20100101 Firefox/46.0',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.5',
            'accept-encoding': 'gzip, deflate, br',
        }

        self.response = self.client.request(
            method='GET',
            url=url,
            headers=headers,
        )

    ### Additional tasks can go here ###


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait = 1000
    max_wait = 3000
```
* Save this code to a .py file. This file is already a useable locust test script, which can be invoked from command-line. For example:

```locust -f <your_file_name.py> --master -H <https://your_server_under_test>```

## Additional Flows
* Now you can pick any additional flows from mitmproxy. For each one, select the flow, and then press the **E** key, which is a shortcut for *Export* and then press **t**, for *locust task*

* Paste the new code immediately under the line
```python
### Additional tasks can go here ###```
in the code above.

* The code will now be similar to:

```python
from locust import HttpLocust, TaskSet, task

class UserBehavior(TaskSet):
    def on_start(self):
        ''' on_start is called when a Locust start before any task is scheduled '''
        self.www_google_com_1461888928_75()

    @task()
    def www_google_com_1461888928_75(self):
        url = self.locust.host + '/'

        headers = {
            ':method': 'GET',
            ':path': '/',
            ':authority': 'www.google.com',
            ':scheme': 'https',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:46.0) Gecko/20100101 Firefox/46.0',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.5',
            'accept-encoding': 'gzip, deflate, br',
        }

        self.response = self.client.request(
            method='GET',
            url=url,
            headers=headers,
        )

    ### Additional tasks can go here ###
    @task()
    def search(self):
        url = self.locust.host + '/search'

        headers = {
            ':method': 'GET',
            ':path': '/search?sclient=psy-ab&site=&source=hp&q=locust.replay+github&oq=locust.replay+github&gs_l=hp.3...6687.6687.0.6769.1.1.0.0.0.0.0.0..0.0....0...1c.1.64.psy-ab..1.0.0.xeEkbM9pnSU&pbx=1&bav=on.2,or.&bvm=bv.120857306,d.cGc&fp=1&biw=1440&bih=740&dpr=2&tch=1&ech=1&psi=oaciV8bVA8r8jwOBsbOABA.1461888929543.3',
            ':authority': 'www.google.com',
            ':scheme': 'https',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:46.0) Gecko/20100101 Firefox/46.0',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.5',
            'accept-encoding': 'gzip, deflate, br',
            'dnt': '1',
            'referer': self.locust.host + '',
        }

        params = {
            'sclient': 'psy-ab',
            'site': '',
            'source': 'hp',
            'q': 'locust.replay github',
            'oq': 'locust.replay github',
        }

        self.response = self.client.request(
            method='GET',
            url=url,
            headers=headers,
            params=params,
        )


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait = 1000
    max_wait = 3000
```

* Repeat for any number of flows.

* Review carefully the generated code, and fix / update headers, params, and any other message component as required. Check also that no indentation mistakes happened during the pasting of the code.

* The new load script will hit also all flows added. Please consult locust documentation for how to tune and tweak this code further.
