from flask import abort, make_response, render_template, redirect, request

from datetime import datetime
from . import api
from .core import app
from .forms import (SendForm, AddressbookForm,
             Addressbook_editForm, Addressbook_deleteForm, ViewForm)
from .pagination import Pagination
from .core import babel
from .config import LANGUAGES
from flask.ext.babel import gettext


MSGS_PER_PAGE = 20
ADDRS_PER_PAGE = 30


@babel.localeselector
def get_locale():
    #return 'en' #for testing
    return request.accept_languages.best_match(LANGUAGES.keys())


def _no_cache(response):
    """Mark a response to never be cached by browser and return it."""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Expires'] = 0
    response.headers['Pragma'] = 'no-cache'

    return response


@app.route('/')
def index():
    return redirect('/inbox')


@app.route('/inbox/', defaults={'page': 1})
@app.route('/inbox/page/<int:page>')
def inbox(page):
    """View for inbox messages."""
    messages = api.get_inbox_messages()

    try:
        pagination = Pagination(page, messages, MSGS_PER_PAGE)
    except IndexError:
        abort(404)  # return not found for pages outside range

    msgs_slice = pagination.get_slice()
    api.decode_and_format_messages(msgs_slice)

    return _no_cache(make_response(render_template("inbox.html",
            messages=msgs_slice, pagination=pagination)))


@app.route('/outbox/', defaults={'page': 1})
@app.route('/outbox/page/<int:page>')
def outbox(page):
    messages = api.get_outbox_messages()

    try:
        pagination = Pagination(page, messages, MSGS_PER_PAGE)
    except IndexError:
        abort(404)  # return not found for pages outside range

    msgs_slice = pagination.get_slice()

    api.decode_and_format_outbox_messages(msgs_slice)

    return _no_cache(make_response(render_template("outbox.html",
            messages=msgs_slice, pagination=pagination)))


@app.route('/viewinbox/<msgid>', methods=['GET', 'POST'])
def viewinbox(msgid):
    """View to display an inbox message."""
    message = api.get_inbox_message_by_id(msgid)
    form = ViewForm()
    viewhtml = True
    if form.validate_on_submit():
        if request.form['btn'] == gettext('ViewHTML'):
            viewhtml = True
        if request.form['btn'] == gettext('ViewNormal'):
            viewhtml = False
        if request.form['btn'] == gettext('Delete'):
            api.delete_message(msgid)
            return redirect('/inbox')
        if request.form['btn'] == gettext('Reply'):
            return redirect('/send/inbox/reply/' + msgid)
        if request.form['btn'] == gettext('Redirect'):
            return redirect('/send/inbox/redirect/' + msgid)
        if request.form['btn'] == gettext('Print'):
            return redirect('/printus/inbox_message/'+msgid)

    return render_template("view.html", message=message, form=form, viewhtml=viewhtml)


@app.route('/viewoutbox/<msgid>', methods=['GET', 'POST'])
def viewoutbox(msgid):
    """View to display an outbox message."""
    message = api.get_outbox_message_by_id(msgid)
    form = ViewForm()
    viewhtml = True
    if form.validate_on_submit():
        if request.form['btn'] == gettext('ViewHTML'):
            viewhtml = True
        if request.form['btn'] == gettext('ViewNormal'):
            viewhtml = False
        if request.form['btn'] == gettext('Delete'):
            api.delete_message(msgid)
            return redirect('/inbox')
        if request.form['btn'] == gettext('Reply'):
            return redirect('/send/inbox/reply/' + msgid)
        if request.form['btn'] == gettext('Redirect'):
            return redirect('/send/inbox/redirect/' + msgid)

    return render_template("view.html", message=message, form=form, viewhtml=viewhtml)


@app.route('/send', defaults={'source': None, 'action': None, 'msgid': None}, methods=['GET', 'POST'])
@app.route('/send/<source>/<action>/<msgid>', methods=['GET', 'POST'])
def send(source, action, msgid):
    form = SendForm()
    form.from_address.choices = []
    form.to_address.choices = []

    if action == 'reply':
        if source == 'inbox':
            message = api.get_inbox_message_by_id(msgid)
        if source == 'outbox':
            message = api.get_outbox_message_by_id(msgid)

        form.message.data = '\n\n\n--Send over BitMessageWebApp https://github.com/Mattze96/BitMessageWebApp--\n------------------------------------------------------\n'+message['message']
     
        #Get real Addresses not Labels, if not API Error in the Daemon, but not in the bmwa.
        real_toAddress = None
        for (k, v) in api.get_address_dict().items():
            if v == message['toAddress']:
                real_toAddress = k
        real_fromAddress = None
        for (k, v) in api.get_identity_dict().items():
            if v == message['fromAddress']:
                real_fromAddress = k
        #If Address not in Addressbook or Identitiesbook:
        if real_fromAddress == None:
            real_fromAddress = message['fromAddress']
        if real_toAddress == None:
            real_toAddress = message['toAddress']        


        form.from_address.choices.append([real_toAddress, message['toAddress']])
        form.to_address.choices.append([real_fromAddress, message['fromAddress']])

        form.subject.data = 'Re: ' + message['subject']

    if action == 'redirect':
        if source == 'inbox':
            message = api.get_inbox_message_by_id(msgid)
        if source == 'outbox':
            message = api.get_outbox_message_by_id(msgid)

        form.message.data = '\n\n\n--Redirected over BitMessageWebApp https://github.com/Mattze96/BitMessageWebApp--\n------------------------------------------------------\n'+message['message']
     
        #Get real Addresses not Labels, if not API Error in the Daemon, but not in the bmwa.
        real_toAddress = None
        for (k, v) in api.get_address_dict().items():
            if v == message['toAddress']:
                real_toAddress = k
        #If Address not in Addressbook or Identitiesbook:
        if real_toAddress == None:
            real_toAddress = message['toAddress']        

        form.from_address.choices.append([real_toAddress, message['toAddress']])

        form.subject.data = 'Aw: ' + message['subject'] #Not sure if it's "AW"

    # Have to get addresses again because form validates against them.
    for (k, v) in sorted(api.get_identity_dict().items()):
        form.from_address.choices.append([k, v]) 

    for (k, v) in sorted(api.get_address_dict().items()):
        form.to_address.choices.append([k, v])

    if form.validate_on_submit():
        form = SendForm()   #Needed because old values will be send.
        api.send_message(form.to_address.data, form.from_address.data,
                    form.subject.data, form.message.data)
        return redirect('/inbox')

    return render_template('send.html', form=form)


@app.route('/addressbook', defaults={'page': 1}, methods=['GET', 'POST'])
@app.route('/addressbook/page/<int:page>')
def addressbook(page):
    """View for Addressbook."""
    addresses = api.get_addressbook_addresses()

    form = AddressbookForm()

    if form.validate_on_submit():
        api.add_addressbookentry(form.new_address.data,
                                form.new_address_label.data)
        return redirect('/addressbook')

    try:
        pagination = Pagination(page, addresses, ADDRS_PER_PAGE)
    except IndexError:
        abort(404)  # return not found for pages outside range

    addrs_slice = pagination.get_slice()

    return _no_cache(make_response(render_template("addressbook.html",
            addresses=addrs_slice, pagination=pagination, form=form)))


@app.route('/addressbook_edit/<address>', methods=['GET', 'POST'])
def addressbook_edit(address):
    form = Addressbook_editForm()

    addresses = api.get_addressbook_addresses()

    for a in addresses:
        if a['address'] == address:
            label = a['label']
            break   # if we have luck, we will save some time:)

    form.old_label.data = label
    form.new_label.data = label

    form.old_address.data = address
    form.new_address.data = address

    if form.validate_on_submit():
        form = Addressbook_editForm()
        api.edit_addressbookentry(address_old=address,
            address_new=form.new_address.data, label_new=form.new_label.data)
        return redirect('/addressbook')

    return render_template("addressbook_edit.html", form=form)


@app.route('/addressbook_remove/<address>', methods=['GET', 'POST'])
def addressbook_remove(address):
    form = Addressbook_deleteForm()

    addresses = api.get_addressbook_addresses()

    for a in addresses:
        if a['address'] == address:
            label = a['label']
            break   # if we have luck, we will save some time:)

    form.label.data = label
    form.address.data = address

    if form.validate_on_submit():
        api.delete_addressbookentry(address=address)
        return redirect('/addressbook')

    return render_template("addressbook_remove.html",
                            form=form, label=label, address=address)


@app.route('/deletemessage/<msgid>')
def deletemessage(msgid):
    
    api.delete_message(msgid=msgid)
    
    return redirect('/inbox')
    

@app.route('/printus/<typus>/<data>')
def printus(typus, data):
    
    if typus == 'inbox_message':
        message = api.get_inbox_message_by_id(data)
        header = '<b>To:</b> '+message['toAddress']
        header += '<br><b>From:</b> '+message['fromAddress']
        header += '<br><b>Subject:</b> '+message['subject']
        header += '<br><b>Date sent:</b> ' +datetime.fromtimestamp(int(message['receivedTime'])).strftime('%Y-%m-%d %H:%M:%S')
        header += '<br><hr><br>'
        main = message['message']#.replace('\n', '<br>')
        return render_template("print.html", header=header, main=main)
    return redirect('/inbox')

    
