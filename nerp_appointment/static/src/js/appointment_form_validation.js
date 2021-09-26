odoo.define('nerp_appointment.FormRegister', function (require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var Widget = require("web.Widget");
    var _t = core._t;

    function format_phoneUS(phoneNumber) {
        var format = "(";
        phoneNumber = phoneNumber.replace(/\D/g, '');
        if (phoneNumber.length === 0) {
            return ''
        } else if (phoneNumber.length > 10) {
            phoneNumber = phoneNumber.slice(0, 10);
        }
        for (var i = 0; i < phoneNumber.length; i++) {
            if (i < 3) {
                format = format + phoneNumber[i];
            } else if (i === 3) {
                format = format + ") " + phoneNumber[i];
            } else if ((i > 3) && (i < 6)) {
                format = format + phoneNumber[i];
            } else if (i === 6) {
                format = format + "-" + phoneNumber[i];
            } else {
                format = format + phoneNumber[i]
            }
        }
        return format;
    }

    function validateEmail(email, restrict = true) {
        var regex = /^([a-zA-Z0-9_.+-])+@(([a-zA-Z0-9-])+\.)+([a-zA-Z0-9]{2,4})+$/;
        var email_domain = email.replace(/.*@/, "@");
        if (restrict) {
            var retricted_emails = [
                "@gmail.com",
                "@outlook.com",
                "@yahoo.com",
                "@icloud.com",
                "@mac.com",
                "@aol.com",
                "@mail.com",
                "@live.com",
                "@msn.com",
                "@comcast.net",
                "@att.net",
                "@hotmail.com",
                "@yopmail.com",
            ];
            if (retricted_emails.includes(email_domain)) {
                return false;
            }
        }
        return regex.test(email);
    }

    function validatePhone(phone) {
        var regex = /^\([0-9]{3}\)\s[\0-9]{3}-[0-9]{4}$/;
        return regex.test(phone);
    }

    function formCheckValidation() {
        if ($("input[name='name']").length) {
            if (!$("input[name='name']").val()) {
                $("input[name='name']").notify("Please enter your Name", "error");
                $('html, body').animate({
                    scrollTop: $("input[name='name']").offset().top - 100
                }, 500);
                return false;
            }
        } 
        if ($("input[name='fname']").length) {
            if (!$("input[name='fname']").val()) {
                $("input[name='fname']").notify("Please enter your First name", "error");
                $('html, body').animate({
                    scrollTop: $("input[name='fname']").offset().top - 100
                }, 500);
                return false;
            }
        }
        if ($("input[name='lname']").length) {
            if (!$("input[name='lname']").val()) {
                $("input[name='lname']").notify("Please enter your Last name", "error");
                $('html, body').animate({
                    scrollTop: $("input[name='lname']").offset().top - 100
                }, 500);
                return false;
            }
        }
        if (!$("input[name='email']").val()) {
            $("input[name='email']").notify("Please enter your email", "error");
            $('html, body').animate({
                scrollTop: $("input[name='email']").offset().top - 100
            }, 500);
            return false;
        }
        if (!validateEmail($("input[name='email']").val(), false)) {
            $("input[name='email']").notify("Please enter a valid email address", "error");
            $('html, body').animate({
                scrollTop: $("input[name='email']").offset().top - 100
            }, 500);
            return false;
        }
        if ($("input[name='phone']").prop('required')) {
            if (!$("input[name='phone']").val()) {
                $("input[name='phone']").notify("Please enter your Phone number", "error");
                $('html, body').animate({
                    scrollTop: $("input[name='phone']").offset().top - 100
                }, 500);
                return false;
            }
        }
        // if ($("input[name='phone']").val()) {
        //     if (!validatePhone($("input[name='phone']").val())) {
        //         $("input[name='phone']").notify("Please enter a valid Phone number", "error");
        //         $('html, body').animate({
        //             scrollTop: $("input[name='phone']").offset().top - 100
        //         }, 500);
        //         return false;
        //     }
        // }
        if ($("input[name='company_name']").prop('required') & ($("input[name='company_name']").val().trim().length < 1)) {
            $("input[name='company_name']").notify("Please enter your Company name", "error");
            $('html, body').animate({
                scrollTop: $("input[name='company_name']").offset().top - 100
            }, 500);
            return false;
        }
        if ($("input#checkbox_other").length > 0 & $("input[id^=question_]").length > 0 & !$("input[id^=question_]").is(":checked") & !$("input#checkbox_other").is(":checked")) {
            $("div#default-topics").notify("Please select the experiences you are interested in.", {
                position: 'top right',
                className: "error"
            })
            $('html, body').animate({
                scrollTop: $("input[id^=question_]").offset().top - 200
            }, 500);
            return false;
        }
        if ($("input#checkbox_other").is(":checked")) {
            if (!$("textarea#other_topics_desc").val()) {
                $("textarea#other_topics_desc").notify("Please tell us more about your requirements", {
                    position: 'top right',
                    className: "error"
                })
                $('html, body').animate({
                    scrollTop: $("textarea#other_topics_desc").offset().top
                }, 500);
                return false;
            }
        }
        if ($('textarea#guests_emails').val()) {
            var guests_emails_str = $('textarea#guests_emails').val()
            var guest_emails = guests_emails_str.split(",")
            var guest_emails_filtered = {}
            for (let email of guest_emails) {
                email = email.trim()
                if (guest_emails_filtered[email]) {
                    $("textarea#guests_emails").notify("There are duplicated guests in your emails' list", {
                        position: 'top right',
                        className: "error"
                    })
                    $('html, body').animate({
                        scrollTop: $("textarea#guests_emails").offset().top - 100
                    }, 500);
                    return false
                } else if (email == $("input[name='email']").val()) {
                    $("textarea#guests_emails").notify("You already are an attendee of this meeting", {
                        position: 'top right',
                        className: "error"
                    })
                    $('html, body').animate({
                        scrollTop: $("textarea#guests_emails").offset().top - 100
                    }, 500);
                    return false
                } else if (!validateEmail(email)) {
                    $("textarea#guests_emails").notify("Please enter a valid email address", {
                        position: 'top right',
                        className: "error"
                    });
                    $('html, body').animate({
                        scrollTop: $("input[name='email']").offset().top - 100
                    }, 500);
                    return false;
                } else {
                    guest_emails_filtered[email] = true
                }
            }
            if (_.size(guest_emails_filtered) > 10) {
                $("textarea#guests_emails").notify("Your guests list can not exceed 10", {
                    position: 'top right',
                    className: "error"
                })
                $('html, body').animate({
                    scrollTop: $("textarea#guests_emails").offset().top - 100
                }, 500);
                return false
            }
        }
        return true;
    }

    var RegisterForm = Widget.extend({
        events: {
            'click #input_submit': 'submitTrialRegisterForm',
            // 'keyup #phone': 'keyUpPhoneFormat',
            'change #email': 'onChangeEmail',
            // 'input #phone': 'onInputPhone',
            // 'change #phone': 'onChangePhone',
            // 'change .i-panel input': 'onChangeInput'
        },
        init: function (parent, options) {
            if ($('fieldset#partner_info').data('is-reschedule')) {
                $('fieldset#partner_info').attr('disabled', 'true')
            }
            this._super.apply(this, arguments);
        },
        // onChangeInput: function(ev){
        //     if($(ev.currentTarget).val()){
        //         var label = $('label[for="' + $(ev.currentTarget).attr('id') + '"]')
        //         label.addClass('active')
        //     }
        // },

        keyUpPhoneFormat: function (ev) {
            $(ev.currentTarget).val(format_phoneUS($(ev.currentTarget).val()));
        },

        onChangeEmail: function (ev) {
            if (!$(ev.currentTarget).val()) {
                $("input[name='email']").notify("Please enter a valid email address", "error");
            } else if (!validateEmail($(ev.currentTarget).val())) {
                $("input[name='email']").notify("Please enter a valid email address", "error");
            }
        },

        onInputPhone: function (ev) {
            if ($("input[name='phone']")) {
                $(ev.currentTarget).val(format_phoneUS($(ev.currentTarget).val()));
            }
        },

        onChangePhone: function (ev) {
            if ($("input[name='phone']")) {
                $(ev.currentTarget).val(format_phoneUS($(ev.currentTarget).val()));
            }
        },

        checkValidateForm: function (){
            return formCheckValidation();
        },

        submitTrialRegisterForm: function (ev) {
            ev.preventDefault();
            var validation = this.checkValidateForm();
            if (validation) {
                var msg = _t("Please wait a second...");
                $.blockUI({
                    'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                        '    <br />' + msg +
                        '</h2>'
                });
                // if ($('input[name="employee"]').val() && $('input[name="employee_id"]').val()) {
                //     // for personal meeting form
                //     var form_data = {}
                //     var form_values = this.$el.serializeArray()
                //     _.each(form_values, function (input) {
                //             form_data[input.name] = input.value
                //         }
                //     )
                //     ajax.post(this.$el.attr('action'), form_data)
                //         .then(function (return_vals) {
                //             return_vals = JSON.parse(return_vals)
                //             if (return_vals.success) {
                //                 $("#failed_message").hide();
                //                 window.location.href = return_vals['url'];
                //             } else {
                //                 $.unblockUI();
                //                 $("#failed_message").find('p#message').text(return_vals['message']);
                //                 $("#failed_message").show();
                //             }
                //         })
                // } else {
                    // for accounting appointment form
                    this.$el.submit()
                // }
            }
        }
    });

    require('web.dom_ready');
    $(window).on("load", function () {
        $.each($("div.i-panel input"), function () {
            if ($(this).val()) {
                $("label[for='" + $(this).attr('id') + "']").addClass('active');
            }
        });
    });
    $('#appointment-form').each(function () {
        var $elem = $(this);
        var item = new RegisterForm();
        item.attachTo($elem);
    });

    return RegisterForm;
});
