## Copyright (C) 2011 Richard Mortier <mort@cantab.net>
##
## This program is free software: you can redistribute it and/or
## modify it under the terms of the GNU Affero General Public License
## as published by the Free Software Foundation, either version 3 of
## the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## Affero General Public License for more details.
##
## You should have received a copy of the GNU Affero General Public
## License along with this program.  If not, see
## <http://www.gnu.org/licenses/>.

import webapp2
import notify.models as models
import notify.views as views

urls = [(r'^/notify/2/?', views.Root),
         ]
routerid_re = r'(?P<routerid>[a-fA-F0-9]+)'
urls += map(
    lambda (p, c): (r'^/notify/2/%s/%s' % (routerid_re, p), c),
    [(r'log/p(?P<pageno>[0-9]+)/?', views.Log),
      (r'log/?',                     views.Log),

      (r'email/?', views.Email),
      (r'twitter/?', views.Twitter),
      (r'phone/?', views.Sms),
      (r'growl/?', views.Growl),

      (r'status/?', views.Status),
      (r'register/?', views.Register),
      (r'add/?', views.AddRouter),
      (r'edit/?', views.EditRegistration),
      (r'delete/?', views.DeleteRegistration),
      ])
application = webapp2.WSGIApplication(urls, debug=False)
