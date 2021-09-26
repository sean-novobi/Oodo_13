odoo.define('nerp_appointment.services_online_booking', function (require) {
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

    var HandlingPackageListing = Widget.extend({
        events: {
            "click a.btn.btn-block.custom-btn-buy.waves-effect.waves-light.buy-package-now.for-package": "_onClick",
        },
        _onClick: function (event) {
            event.preventDefault();
            if ($.blockUI) {
                var msg = _t("Please wait a second...");
                $.blockUI({
                    'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                        '    <br />' + msg +
                        '</h2>'
                });
                window.location.href = $(event.target).attr('href');
            }
        }
    })

    var HandlingCalendarSlot = Widget.extend({
            events: {
                "click button#services-continue-booking": "continueServicesBooking",
                "click td.o_day.dropdown a.dropdown-item.new, td.o_day.dropdown a.dropdown-item.reschedule": 'passDataModal',
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
            formatSelectedSessionDatetime: function (datetime_str, duration) {
                // debugger;
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
                $('#services-continue-booking').attr('data-slot-datetime', $(event.target).data('slot-datetime'));
                $('#services-continue-booking').attr('data-employee-id', $(event.target).data('employee-id'));
                $('#services-continue-booking').attr('data-access-token', $(event.target).data('access-token'));
                $('#services-continue-booking').attr('data-datetime-format', datetime_format)

                if ($(event.target).hasClass('reschedule')) {
                    $('#services-continue-booking').attr('data-reschedule', true);
                } else if ($(event.target).hasClass('new')) {
                    $('#services-continue-booking').attr('data-reschedule', false);
                }
            },
            continueServicesBooking: function (event) {
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
                    '/services/appointment/reschedule', 'call', {
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
                        debugger;
                        $.unblockUI();
                        $("#failed_message").find('p#message').text(return_vals['message']);
                        $("#failed_message").show();
                    }
                })

            },

            checkSlot: function (event) {
                event.preventDefault();
                //We block sreen because we need to call Ajax to server
                debugger;
                // Something wrong with the .data() function of jQuery. It keep using old data despite selecting new time slot
                var datetime_str = $(event.target).attr('data-slot-datetime');
                var employee_id = $(event.target).data('employee-id');
                var access_token = $(event.target).data('access-token');
                var msg = _t("Please wait a second...");
                $.blockUI({
                    'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                        '    <br />' + msg +
                        '</h2>'
                });
                ajax.jsonRpc(
                    '/services/appointment/check_slot_appointment', 'call', {
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
                        debugger;
                        $.unblockUI();
                        $("#failed_message").find('p#message').text(return_vals['message']);
                        $("#failed_message").show();
                    }
                })
                
            },
        })
    ;

    $("#services_appointment_calendar").each(function () {
        var $el = $(this);
        var item = new HandlingCalendarSlot();
        item.attachTo($el)
    });

    $("div#packages_list").each(function () {
            var $el = $(this);
            var item = new HandlingPackageListing()
            item.attachTo($el)
        }
    )


})