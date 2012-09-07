
"""
Query Web search engines.

This module works by filtering the HTML returned by the search engine and thus tends to break when
search engines modify their HTML output.

Public domain, Connelly Barnes 2005-2007.  Compatible with Python 2.3-2.5.

See L{examples} for a quick start.  See L{description} for the full
explanation, precautions, and legal disclaimers.

"""

import re
import time
import urllib
import urllib2
import weakref
import threading
import Queue

__version__ = '1.0.3'

# Default headers for HTTP requests.
DEFAULT_HEADERS = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5)'}

# Default maximum number of results.
DEFAULT_MAX_RESULTS = 10

# Function names for supported search engines.
SEARCH_ENGINES = ['ask', 'dmoz', 'excite', 'google', 'msn', 'yahoo']

__all__ = SEARCH_ENGINES + ['examples', 'description']

# --------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------

def quote_plus(s):
  """
  A variant of urllib.quote_plus which handles ASCII and Unicode.
  """
  return urllib.quote_plus(s.encode('utf-8'))


def read_url(url, headers=DEFAULT_HEADERS, blocking=True):
  """
  Read str contents of given str URL.

  Here headers is a map of str -> str for HTTP request headers.  If
  blocking is True, returns the str page contents.  If blocking is
  False, returns an iterator which gives None until a successful read,
  at which point the str page contents is yielded.
  """
  req = urllib2.Request(url, None, headers)
  return urllib2.urlopen(req).read()


def fix_url(url):
  """
  Given url str, trim redirect stuff and return actual URL.

  Currently this just returns the URL unmodified.
  """
#  if url.lower().find('http%3a//') > 0:
#    return 'http://' + url[url.lower().rindex('http%3a//')+9:]
#  if url.find('http://') > 0:
#    return url[url.rindex('http://'):]
  return url


def get_search_page_links(page, results_per_page, begin, end, link_re):
  """
  Given str contents of search result page, return list of links.

  Returns list of (name, url, desc) str tuples.  See make_searcher()
  for a description of results_per_page and link_re.
  """
  if begin is not None and begin in page:
    page = page[page.index(begin):]
  if end is not None and end in page:
    page = page[:page.index(end)]
  ans = []
  for match in re.compile(link_re, re.DOTALL).finditer(page):
    (name, url, desc) = match.group('name', 'url', 'desc')
    url = fix_url(url)
    ans += [(html_to_text(name), url, html_to_text(desc))]
  return ans


def html_to_text(s):
  """
  Given an HTML formatted str, convert it to a text str.
  """
  s = re.sub(r'<.*?>', '', s)
  s = s.replace('\r', ' ')
  s = s.replace('\n', ' ')
  s = s.replace('\t', ' ')
  s = s.replace('&amp;', '&')
  s = s.replace('&lt;', '<')
  s = s.replace('&gt;', '>')
  s = s.replace('&quot;', '"')
  s = s.replace('&middot;', '\xb7')
  for i in range(256):
    s = s.replace('&#%d;' % i, chr(i))
  while s.replace('  ', ' ') != s:
    s = s.replace('  ', ' ')
  return s.strip()


def nonblocking(f, blocking_return=None, sleep_time=0.01):
  """
  Wrap a callable which returns an iter so that it no longer blocks.

  The wrapped iterator returns blocking_return while callable f is
  blocking.  The callable f is called in a background thread.  If the
  wrapped iterator is deleted, then the iterator returned by f is
  deleted also and the background thread is terminated.
  """
  def g(*args, **kwargs):
    f_iter = f(*args, **kwargs)
    g_iter = None
    def run():
      while True:
        g_obj = g_iter()
        if g_obj is None:
          return
        if g_obj.q.qsize() == 0:
          try:
            f_next = f_iter.next()
          except Exception, e:
            g_obj.exc = e
            return
          g_obj.q.put(f_next)
        else:
          del g_obj
          time.sleep(sleep_time)
    class Iter:
      def __init__(self):
        self.q = Queue.Queue()
        self.exc = None
        self.thread = threading.Thread(target=run)
        self.thread.setDaemon(True)
      def next(self):
        if self.exc is not None:
          raise self.exc
        try:
          return self.q.get_nowait()
        except Queue.Empty:
          return blocking_return
      def __iter__(self):
        return self

    obj = Iter()
    g_iter = weakref.ref(obj)
    obj.thread.start()
    try:
      return obj
    finally:
      del obj
  return g


def make_searcher(query_url, results_per_page, page_url, page_mode,
                  begin, end, link_re):
  """
  Return a search function for the given search engine.

  Here query_url is the URL for the initial search, with %(q)s for
  the query string, results_per_page is the number of search results
  per page, page_url is the URL for the 2nd and subsequent pages of
  search results, with %(q)s for the query string and %(n)s for the
  page "number."  Here page_mode controls the actual value for the
  page "number:"

   - page_mode='page0':   Use 0-based index of the page.
   - page_mode='page1':   Use 1-based index of the page.
   - page_mode='offset0': Use 0-based index of the search result,
                          which is a multiple of results_per_page.
   - page_mode='offset1': Use 1-based index of the search result
                          (one plus a multiple of results_per_page).

  If begin is not None, then only text after the first occurrence of
  begin will be used in the search results page.  If end is not None,
  then only text before the first occurrence of end will be used.

  Finally, link_re is a regex string (see module re) which matches
  three named groups: 'name', 'url', and 'desc'.  These correspond to
  the name, URL and description of each search result.  The regex is
  applied in re.DOTALL mode.

  Returns a search() function which has the same interface as
  described in the module docstring.
  """
  def search_blocking(query, max_results):
    last_links = None
    page_num = 0
#    done = False
    q = Queue.Queue()
    for i in range(max_results):
      if q.qsize() == 0:
        if page_num == 0:
          page = read_url(query_url % {'q': quote_plus(query)})
        else:
#          if done:
#            break
          if page_mode == 'page0':
            n = page_num
          elif page_mode == 'page1':
            n = page_num + 1
          elif page_mode == 'offset0':
            n = page_num * results_per_page
          elif page_mode == 'offset1':
            n = page_num * results_per_page + 1
          else:
            raise ValueError('unknown page mode')
          page = read_url(page_url % {'n': n, 'q': quote_plus(query)})
        page_num += 1
        links = get_search_page_links(page, results_per_page, begin, end, link_re)
        if len(links) == 0 or links == last_links:
          break
#        if len(links) < results_per_page:
#          done = True
        last_links = links
        for link in links:
          q.put(link)
      yield q.get()

  search_nonblocking = nonblocking(search_blocking)

  def search(query, max_results=DEFAULT_MAX_RESULTS, blocking=True):
    """
    See docstring for web_search module.
    """
    if blocking:
      return search_blocking(query, max_results)
    else:
      return search_nonblocking(query, max_results)

  return search


def examples():
  """
  Examples of the web_search module.

  Example 1:

   >>> from web_search import google
   >>> for (name, url, desc) in google('python', 20):
   ...   print name, url
   ...
   (First 20 results for Google search of "python").

  Example 2:

   >>> from web_search import dmoz
   >>> list(dmoz('abc', 10))
   [('ABC.com', 'http://www.abc.com', "What's on ABC..."), ...]

  """
  print examples.__doc__


def description():
  """
  Full explanation and precautions for web_search module.

  The search functions in this module follow a common interface::

      search(query, max_results=10, blocking=True) =>
        iterator of (name, url, description) search results.

  Here query is the query string, max_results gives the maximum number
  of search results, and the items in the returned iterator are string
  3-tuples containing the Website name, URL, and description for each
  search result.

  If blocking=False, then an iterator is returned which does not block
  execution: the iterator yields None when the next search result is
  not yet available (a background thread is created).

  Supported search engines are 'ask', 'dmoz', 'excite', 'google', 'msn',
  'yahoo'.  This module is not associated with or endorsed by any of
  these search engine corporations.

  Be warned that if searches are made too frequently, or max_results is
  large and you enumerate all search results, then you will be a drain
  on the search engine's bandwidth, and the search engine organization
  may respond by banning your IP address or IP address range.

  This software has been placed in the public domain with the
  following legal notice::

        This software is provided "as is," without warranty of any kind,
        either express or implied, including but not limited to the
        warranties of merchantability and fitness for a particular purpose.
        In no event shall the author(s) of the work be held liable for any
        damages or other liability, including but not limited to general,
        special, incidental, or consequential damages (including but not
        limited to damages to equipment, data, or profit sustained by you
        or third parties), even if any of the parties has been advised of
        the possibility of such damages.

  """
  print description.__doc__


# --------------------------------------------------------------------
# Search engines
# --------------------------------------------------------------------

ask       = make_searcher('http://www.ask.com/web?q=%(q)s', 10,
                          'http://www.ask.com/web?page=%(n)d&q=%(q)s', 'page1',
                          None, None,
                          r'<a .*? class="L4" href="(?P<url>.*?)".*?>(?P<name>.*?)</a>' +
                          r'.*?</div>(?P<desc>.*?)</div>')

dmoz      = make_searcher('http://search.dmoz.org/cgi-bin/search?search=%(q)s', 20,
                          'http://search.dmoz.org/cgi-bin/search?start=%(n)d&search=%(q)s', 'offset1',
                          None, None,
                          r'<li><a href="(?P<url>.*?)".*?>(?P<name>.*?)</a>' +
                          r'.*? - (?P<desc>.*?)<br>')

excite    = make_searcher('http://msxml.excite.com/info.xcite/search/web/%(q)s', 20,
                          'http://msxml.excite.com/info.xcite/search/web/%(q)s/%(n)d', 'offset1',
                          None, None,
                          r'<div class="listingmain" style=""><a href="(?P<url>.*?)".*?>(?P<name>.*?)</a>' +
                          r'(?P<desc>.*?)</span>')

google    = make_searcher('http://www.google.com/search?q=%(q)s', 10,
                          'http://www.google.com/search?start=%(n)d&q=%(q)s', 'offset0',
                          None, None,
                          r'<a href="(?P<url>[^"]*?)" class=l.*?>(?P<name>.*?)</a>' +
                          r'.*?(?:<br>|<table.*?>)' +
                          r'(?P<desc>.*?)' + '(?:<font color=#008000>|<a)')

msn       = make_searcher('http://search.live.com/results.aspx?q=%(q)s', 10,
                          'http://search.live.com/results.aspx?q=%(q)s&first=%(n)d', 'offset1',
                          None, None,
                          r'<h3><a href="(?P<url>.*?)".*?>(?P<name>.*?)</a>' +
                          r'</h3><p>(?P<desc>.*?)</p>')

yahoo     = make_searcher('http://search.yahoo.com/search?p=%(q)s', 10,
                          'http://search.yahoo.com/search?p=%(q)s&b=%(n)d', 'offset1',
                          None, None,
                          r'<li><div class="res"><div><h3><a class="yschttl spt" href="(?P<url>.*?)".*?>(?P<name>.*?)</a>' +
                          r'</h3></div><div class="abstr">(?P<desc>.*?)</div>')

# --------------------------------------------------------------------
# Unit tests
# --------------------------------------------------------------------

def test_engine(search):
  """
  Test a search engine function returned by make_searcher().
  """
  for query in ['abc', 'microsoft', 'love', 'pweropieiw', 'addfdae']:
    popular = query in ['abc', 'microsoft', 'love', 'run']
    for n in [6, 17, 31]:
      n1 = len(list(search(query, n)))
      if popular:
        assert n1 == n
      else:
        assert n1 <= n
      n2 = 0
      for item in search(query, n, False):
        if item is not None:
          n2 += 1
        else:
          time.sleep(0.01)
      if popular:
        assert n2 == n
      else:
        assert n2 <= n


def test():
  """
  Unit test main routine.
  """
  import inspect
  print 'Testing:'
  for name in SEARCH_ENGINES:
    print '  ' + (name + ':').ljust(20),
    test_engine(getattr(inspect.getmodule(test), name))
    print 'OK'


if __name__ == '__main__':
  test()
