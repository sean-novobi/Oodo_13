odoo.define('nerp_appointment.personal_online_booking', function (require) {
    "use strict";

    require('web.dom_ready');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var ajax = require('web.ajax');
    var _t = core._t;

    if ($.blockUI) {
        // our message needs to appear above the modal dialog
        $.blockUI.defaults.baseZ = 2147483647; //same z-index as StripeCheckout
        $.blockUI.defaults.css.border = '0';
        $.blockUI.defaults.css["background-color"] = '';
        $.blockUI.defaults.overlayCSS["opacity"] = '0.9';
    }

    var HandlingCalendarSlot = Widget.extend({
            events: {
                "click td.o_day.dropdown a.dropdown-item.new, td.o_day.dropdown a.dropdown-item.reschedule": 'passDataModal',
                "click button#personal-continue-booking": "continuePersonalBooking",
                "click button.go-next": "goNext",
                "click button.go-prev": "goPrev",
                "click button#add-guests": "addGuests",
            },

            init: function () {
                $('td.o_day.dropdown a.dropdown-item.new, td.o_day.dropdown a.dropdown-item.reschedule').each(function () {
                    var self = $(this)
                    var new_hour = moment(this.text, 'HH').format('LT')
                    self.text(new_hour)
                })
                if ($('input[name="datetime_str"]').val()) {
                    var datetime_format = this.formatSelectedSessionDatetime($('input[name="datetime_str"]').val(), $('input[name="duration"]').val())
                    $('#datetime-format').text(datetime_format)
                }
                if ($('div#calendar_0')) {
                    $('div#calendar_0').toggle()
                }
                $('#robot_warning').delay(2000).fadeOut(500)
            },

            goNext: function (ev) {
                var next_month_id = $(ev.target).data('next-month-id')
                var next_month = $('#' + next_month_id)
                if (next_month) {
                    next_month.toggle();
                    var next_month_index = $(ev.target).data('month-index')
                    $('#calendar_' + String(next_month_index - 1)).toggle()
                }
            },
            goPrev: function (ev) {
                var prev_month_id = $(ev.target).data('prev-month-id')
                var prev_month = $('#' + prev_month_id)
                if (prev_month) {
                    prev_month.toggle();
                    var prev_month_index = $(ev.target).data('month-index')
                    $('#calendar_' + String(prev_month_index + 1)).toggle()
                }
            },
            formatSelectedSessionDatetime: function (datetime_str, duration) {
                var start_datetime_locale = moment.tz(datetime_str, $('#timezone').data('timezone'))
                var duration = duration
                // The convention for novobi appointments is that they start and end in the same date
                var start_datetime_locale_str = start_datetime_locale.format('LLLL');
                var end_datetime_locale_str = moment(start_datetime_locale).add(duration, 'hours').format('LT z')
                var datetime_format = start_datetime_locale_str + ' - ' + end_datetime_locale_str
                return datetime_format
            },
            passDataModal: function (event) {
                var datetime_format = this.formatSelectedSessionDatetime($(event.target).data('slot-datetime'), $(event.target).data('duration'))
                $('#booking-confirmation #datetime-locale').text(datetime_format);
                $('#personal-continue-booking').attr('data-slot-datetime', $(event.target).data('slot-datetime'));
                $('#personal-continue-booking').attr('data-employee-id', $(event.target).data('employee-id'));
                $('#personal-continue-booking').attr('data-access-token', $(event.target).data('access-token'));
                $('#personal-continue-booking').attr('data-datetime-format', datetime_format)

                if ($(event.target).hasClass('reschedule')) {
                    $('#personal-continue-booking').attr('data-reschedule', true);
                } else if ($(event.target).hasClass('new')) {
                    $('#personal-continue-booking').attr('data-reschedule', false);
                }
            },

            continuePersonalBooking: function (event) {
                event.preventDefault();
                if ($(event.target).data('reschedule')) {
                    this.reschedule(event)
                } else {
                    this.checkSlot(event)
                }
            },

            reschedule: function (event) {
                event.preventDefault();
                //We block sreen because we need to call Ajax to server
                var msg = _t("Please wait a second...");
                $.blockUI({
                    'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                        '    <br />' + msg +
                        '</h2>'
                });

                var datetime_str = $(event.target).attr('data-slot-datetime');
                var employee_id = $(event.target).data('employee-id');
                var access_token = $(event.target).data('access-token');
                ajax.jsonRpc(
                    '/booking/appointment/reschedule', 'call', {
                        'datetime_str': datetime_str,
                        'employee_id': employee_id,
                        'access_token': access_token,
                    }
                ).then(function (return_vals) {
                    $(".modal").modal("hide");
                    if (return_vals['success']) {
                        $("#failed_message").hide();
                        window.location.href = return_vals['url'];
                    } else {
                        $.unblockUI();
                        $("#failed_message").find('p#message').text(return_vals['message']);
                        $("#failed_message").show();
                    }
                })

            },

            checkSlot: function (event) {
                event.preventDefault();
                //We block sreen because we need to call Ajax to server
                // Something wrong with the .data() function of jQuery. It keep using old data despite selecting new time slot
                var datetime_str = $(event.target).attr('data-slot-datetime');
                var datetime_format = $(event.target).attr('data-datetime-format');
                $('#booking-confirmation').modal('hide');
                $('input[name="datetime_str"]').val(datetime_str);
                $('#time_selected').show();
                $('#select_time_warning').hide();
                $('#datetime-format').text(datetime_format);
                $('input[name="employee_id"]').val($(event.target).attr('data-employee-id'));
                if ($('input[name="datetime_str"]').val()) {
                    $('button#input_submit').removeAttr('disabled');
                }
        },
            addGuests: function(event){
                event.preventDefault();
                $('div#add-guests-section').show();
                $('button#add-guests').hide();
            }
        })
    ;

    $("#personal_appointment_calendar").each(function () {
        var $el = $(this);
        var item = new HandlingCalendarSlot();
        item.attachTo($el);
    });

})