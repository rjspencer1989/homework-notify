## Copyright (C) 2011 Richard Mortier <rmm@cs.nott.ac.uk>
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


class NotFound(webapp2.RequestHandler):
    '''Page not found view handler.'''

    def get(self):
        self.redirect("http://www.homenetworks.ac.uk/")

application = webapp2.WSGIApplication([('^/.*', NotFound), ], debug=False)
