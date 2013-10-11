from flask import abort, make_response, render_template, redirect

from . import api
from .core import app
from .forms import SendForm


MSGS_PER_PAGE = 20


@app.route('/')
def index():
    return redirect('/inbox')


@app.route('/inbox/', defaults={'page': 1})
@app.route('/inbox/page/<int:page>')
def inbox(page):
    """View for inbox messages."""
    messages = api.get_inbox_messages()
    mtotal = len(messages)

    page_count = 1 + mtotal // MSGS_PER_PAGE
    if page < 1 or page > page_count:
        abort(404)  # return not found for pages outside range

    mstart, mstop = (page - 1) * MSGS_PER_PAGE, page * MSGS_PER_PAGE
    mstop = min(mstop, mtotal)
    msgs_slice = messages[mstart: mstop]

    api.decode_and_format_messages(msgs_slice)

    response = make_response(render_template("inbox.html",
            messages=msgs_slice, page=page, page_count=page_count,
            mstart=mstart, mstop=mstop, mtotal=mtotal))

    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Expires'] = 0  # force reload so messages marked read
    response.headers['Pragma'] = 'no-cache'

    return response

@app.route('/outbox', defaults={'page': 1})
@app.route('/outbox/page/<int:page>')
def outbox(page):
    messages = api.get_outbox_messages()
    mtotal = len(messages)

    page_count = 1 + mtotal // MSGS_PER_PAGE
    if page < 1 or page > page_count:
        abort(404)  # return not found for pages outside range

    mstart, mstop = (page - 1) * MSGS_PER_PAGE, page * MSGS_PER_PAGE
    mstop = min(mstop, mtotal)
    msgs_slice = messages[mstart: mstop]

    api.decode_and_format_outbox_messages(msgs_slice)

    response = make_response(render_template("outbox.html",
            messages=msgs_slice, page=page, page_count=page_count,
            mstart=mstart, mstop=mstop, mtotal=mtotal))

    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Expires'] = 0  # force reload so messages marked read
    response.headers['Pragma'] = 'no-cache'

    return response



@app.route('/view/<msgid>')
def view(msgid):
    """View to display an inbox message."""
    message = api.get_inbox_message_by_id(msgid)

    return render_template("view.html", message=message)


@app.route('/send', methods=['GET', 'POST'])
def send():
    form = SendForm()
    # Have to get addresses again because form validates against them.
    form.from_address.choices = [(k, v) for
                (k, v) in sorted(api.get_identity_dict().items())]
    form.to_address.choices = [(k, v) for
                (k, v) in sorted(api.get_address_dict().items())]

    if form.validate_on_submit():
        api.send_message(form.to_address.data, form.from_address.data,
                    form.subject.data, form.message.data)
        return redirect('/inbox')

    return render_template('send.html', form=form)
