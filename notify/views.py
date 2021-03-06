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

import logging
import urllib
import urllib2
import datetime
import hashlib
import base64
log = logging.info

from google.appengine.api import urlfetch
import webapp2
import json
from google.appengine.api import mail

import notify.models as models
import secrets
import oauth


class Root(webapp2.RequestHandler):
    def get(self):
        routerid = models.DEFAULT_ROUTER_ID
        while routerid == models.DEFAULT_ROUTER_ID:
            n = models.Router.all().count()
            d = datetime.datetime.now().isoformat()
            routerid = hashlib.sha1("%s:%s" % (n, d)).hexdigest()
        self.response.out.write(routerid)


class AddRouter(webapp2.RequestHandler):
    def post(self, routerid):
        r = models.Router.all().filter("routerid = ", routerid).get()
        if r:
            self.response.out.write("Router already exists")
            return
        routerName = self.request.get("name")
        models.Router(routerid=routerid, name=routerName).put()


class DeleteRegistration(webapp2.RequestHandler):
    def post(self, routerid):
        r = models.Router.all().filter("routerid =", routerid).get()
        if not r:
            self.response.out.write("Router not found")
            log("Router not found")
            self.response.set_status(404)
            return
        requestedSuid = self.request.get("suid")
        if not requestedSuid:
            self.response.out.write("No Service Use ID entered. Stopping")
            self.set_status(400)
            log("no suid entered")
            return
        suid = models.ServiceUse.all().filter("suid =", requestedSuid).get()
        if not suid:
            self.response.out.write("Service use mot found. Stopping")
            self.response.set_status(404)
            log("suid not found")
            return
        suid.delete()
        self.response.set_status(200)

class EditRegistration(webapp2.RequestHandler):
    def post(self, routerid):
        r = models.Router.all().filter("routerid =", routerid).get()
        if not r:
            self.response.out.write("Router not found")
            log("Router not found")
            self.response.set_status(404)
            return
        requestedSuid = self.request.get("suid")
        if not requestedSuid:
            self.response.out.write("No Service Use ID entered. Stopping")
            self.set_status(400)
            log("no suid entered")
            return
        suid = models.ServiceUse.all().filter("suid =", requestedSuid).get()
        if not suid:
            self.response.out.write("Service use mot found. Stopping")
            self.response.set_status(404)
            log("suid not found")
            return
        requestedEndpoint = self.request.get("userdetails")
        if not requestedEndpoint:
            self.response.out.write("No user details entered. Stopping")
            self.response.set_status(400)
            log("no user details entered")
            return
        serviceUseId = generate_suid(routerid, suid.service, requestedEndpoint)
        requestedService = suid.service
        suid.delete()
        models.ServiceUse(service=requestedService, router=r, endpoint=requestedEndpoint, suid=serviceUseId).put()
        self.response.out.write(serviceUseId)
        self.response.set_status(200)


class Register(webapp2.RequestHandler):
    def post(self, routerid):
        r = models.Router.all().filter("routerid =", routerid).get()
        if not r:
            self.response.out.write("Router not found")
            log("Router not found")
            self.response.set_status(404)
            return
        requestedService = self.request.get("service")
        if not requestedService:
            self.response.out.write("No Service entered. Stopping")
            self.response.set_status(400)
            log("no service entered")
            return
        s = models.Service.get_by_key_name(requestedService)
        if not s:
            self.response.out.write("Service not found. Stopping")
            self.response.set_status(404)
            log("service not found.")
            return
        requestedEndpoint = self.request.get("userdetails")
        if not requestedEndpoint:
            self.response.out.write("No user details entered. Stopping")
            self.response.set_status(400)
            log("no user details entered")
            return

        serviceUseId = generate_suid(routerid, requestedService, requestedEndpoint)
        models.ServiceUse(service=s, router=r, endpoint=requestedEndpoint, suid=serviceUseId).put()
        self.response.out.write(serviceUseId)
        self.response.set_status(200)


class Log(webapp2.RequestHandler):
    def get(self, routerid, pageno=None):
        r = models.Router.all().filter("routerid =", routerid).get()
        if not r:
            self.response.out.write("No Router found")
            self.response.set_status(404)
            return

        les = sorted([le.todict() for s in r.services for le in s.log_entries], key=lambda le: le['ts'])
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(les, indent=2))


def json_services_used(r, s):
    s = models.Service.get_by_key_name(s)
    r = models.Router.all().filter("routerid =", r).get()
    if not r:
        return ""

    return json.dumps(
        [su.todict() for su in r.services.filter("service =", s)],
        indent=2)


def log_notification(to, body, sus):
    serviceUsed = None
    for su in sus:
        if su.endpoint == to:
            serviceUsed = su
    if not serviceUsed:
        return
    s = models.Service.get_by_key_name("email")
    emailbody = "Sent message: %s to %s from %s (%s) using service %s" % (body, to, serviceUsed.router.routerid, serviceUsed.router.name, serviceUsed.service.key().name())
    message = mail.EmailMessage(sender=s.endpoint, subject="Homework Router Notification sent")
    message.to = secrets.ETHNOGRAPHY_EMAIL
    message.body = emailbody
    message.send()

    models.Log(msg="Sent message: %s to %s" % (body, to), svcu=serviceUsed).put()


def generate_suid(routerid, service, endpoint):
    d = datetime.datetime.now().isoformat()
    return hashlib.sha1("%s:%s:%s:%s" % (routerid, service, endpoint, d)).hexdigest()


def generate_notification_id(routerid):
    n = models.NotifyResult.all().count()
    d = datetime.datetime.now().isoformat()
    notificationId = hashlib.sha1("%s:%s:%s" % (routerid, n, d)).hexdigest()
    return notificationId


class Status(webapp2.RequestHandler):
    def post(self, routerid):
        u = models.Router.all().filter("routerid =", routerid).get()
        if not u:
            self.response.out.write("Router not found. Can't request status")
            self.response.set_status(404)
            return
        status = self.request.get("notification")
        if not status:
            self.response.out.write("No notification ID entered. Can't get status.")
            self.response.set_status(400)
            return
        notificationResult = models.NotifyResult.all().filter("notification =", status).get()
        if not notificationResult:
            self.response.out.write("No Notification found with that ID. Stopping")
            self.response.set_status(404)
            return
        resultDict = notificationResult.todict()
        if not resultDict:
            self.response.out.write("Error retrieving status.")
            self.response.set_status(400)
            return
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(resultDict, indent=2))


class Email(webapp2.RequestHandler):
    def post(self, routerid):
        if routerid == models.DEFAULT_ROUTER_ID:
            return
        r = models.Router.all().filter("routerid =", routerid).get()
        if not r:
            self.response.out.write("Router not found. Can't send notification")
            self.response.set_status(404)
            return

        s = models.Service.get_by_key_name("email")
        sus = r.services.filter("service =", s).fetch(100)
        if not sus:
            self.response.out.write("no email addresses available to send to")
            self.response.set_status(404)
            return

        body = self.request.get("body")
        if not body:
            self.response.out.write("no message given")
            self.response.set_status(400)
            return

        to = self.request.get("to")
        if not to:
            self.response.out.write("No email address entered")
            self.response.set_status(400)
            return
        registered_emails = [su.endpoint for su in sus]
        if to not in registered_emails:
            self.response.out.write("Unknown email address entered. Unable to send message")
            self.response.set_status(404)
            return

        log("EMAIL: user:%s to:%s body:\n%s\n--\n" % (
            r.name, to, body))

        message = mail.EmailMessage(sender=s.endpoint, subject="Homework Router Notification!")
        message.to = to
        message.body = body
        message.send()
        log_notification(to, body, sus)
        self.response.out.write("email sent")

    def get(self, routerid):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json_services_used(routerid, "email"))


class Twitter(webapp2.RequestHandler):
    def post(self, routerid):
        if routerid == models.DEFAULT_ROUTER_ID:
            return
        r = models.Router.all().filter("routerid =", routerid).get()
        if not r:
            self.response.out.write("Router not found. Can't send notification")
            self.response.set_status(404)
            return

        s = models.Service.get_by_key_name("twitter")
        sus = r.services.filter("service =", s).fetch(100)
        if not sus:
            self.response.out.write("No Twitter accounts available to send to")
            self.response.set_status(404)
            return

        body = self.request.get("body")
        if not body:
            self.response.out.write("No message given. Nothing to send")
            self.response.set_status(400)
            return

        to = self.request.get("to")
        if not to:
            self.response.out.write("No Twitter Account Name entered")
            self.response.set_status(400)
            return
        registered_eps = [su.endpoint for su in sus]
        if to not in registered_eps:
            self.response.out.write("Unknown Twitter account entered. Unable to send message")
            self.response.set_status(404)
            return

        log("TWITTER: user:%s to:%s body:\n%s\n--\n" % (r.name, to, body))

        client = oauth.TwitterClient(
            secrets.TWITTER_CONSUMER_KEY,
            secrets.TWITTER_CONSUMER_SECRET,
            None
            )

        resp = client.make_request(
            "https://api.twitter.com/1.1/direct_messages/new.json",
            token=secrets.TWITTER_ACCESS_TOKEN,
            secret=secrets.TWITTER_ACCESS_TOKEN_SECRET,
            additional_params={'text': body, 'screen_name': to, },
            method=urlfetch.POST,
            )

        log("result: %s -- %s -- %s -- %s" % (resp, resp.status_code, resp.headers, resp.content))
        log_notification(to, body, sus)
        notificationId = generate_notification_id(routerid)
        models.NotifyResult(statusCode=resp.status_code, statusMessage=resp.content, notification=notificationId, router=r).put()
        self.response.out.write(notificationId)

    def get(self, routerid):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json_services_used(routerid, "twitter"))


class Sms(webapp2.RequestHandler):
    def post(self, routerid):
        if routerid == models.DEFAULT_ROUTER_ID:
            return
        r = models.Router.all().filter("routerid =", routerid).get()
        if not r:
            self.response.out.write("Router not found. Can't send notification")
            self.response.set_status(404)
            return

        s = models.Service.get_by_key_name("phone")
        sus = r.services.filter("service =", s).fetch(100)
        if not sus:
            self.response.out.write("No Phones available to send to")
            self.response.set_status(404)
            return

        body = self.request.get("body")
        if not body:
            self.response.out.write("No message given. Nothing to send")
            self.response.set_status(400)
            return

        to = self.request.get("to")
        if not to:
            self.response.out.write("No Phone number entered")
            self.response.set_status(400)
            return
        registered_phones = [su.endpoint for su in sus]
        if to not in registered_phones:
            self.response.out.write("Unknown phone number entered. Unable to send message")
            self.response.set_status(404)
            return

        log("PHONE: user:%s to:%s body:\n%s\n--\n" % (r.name, to, body))
        smsToken = secrets.PHONE_TOKEN
        dict = {'numberToDial': to, 'message': body}
        data = urllib.urlencode(dict)
        theurl = "https://api.tropo.com/1.0/sessions?action=create&token=%s&%s" % (smsToken, data)
        resp = urlfetch.fetch(theurl)
        log("result: %s -- %s -- %s -- %s" % (resp, resp.status_code, resp.headers, resp.content))
        log_notification(to, body, sus)
        notificationId = generate_notification_id(routerid)
        models.NotifyResult(statusCode=resp.status_code, statusMessage=resp.content, notification=notificationId, router=r).put()
        self.response.out.write(notificationId)

    def get(self, routerid):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json_services_used(routerid, "phone"))


class Growl(webapp2.RequestHandler):
    def post(self, routerid):
        if routerid == models.DEFAULT_ROUTER_ID:
            return
        r = models.Router.all().filter("routerid =", routerid).get()
        if not r:
            self.response.out.write("Router not found. Can't log notification")
            self.response.set_status(404)
            return

        s = models.Service.get_by_key_name("growl")
        sus = r.services.filter("service =", s).fetch(100)
        if not sus:
            self.response.out.write("No Growl clients available. Can't log the notification")
            self.response.set_status(404)
            return

        body = self.request.get("body")
        if not body:
            self.response.out.write("No message given. Nothing to log")
            self.response.set_status(400)
            return

        to = self.request.get("to")
        if not to:
            self.response.out.write("No IP Address entered, can't log notification without destination")
            self.response.set_status(400)
            return
        registered_devices = [su.endpoint for su in sus]
        if to not in registered_devices:
            self.response.out.write("Unknown IP Address entered. Unable to log message")
            self.response.set_status(404)
            return

        log("GROWL: user:%s to:%s body:\n%s\n--\n" % (r.name, to, body))
        log_notification(to, body, sus)
        self.response.out.write("Growl notification sent")

    def get(self, routerid):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json_services_used(routerid, "growl"))
