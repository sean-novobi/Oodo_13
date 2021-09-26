odoo.define('nerp_appointment.appointment_calendar', function (require) {
    "use strict";

    require('web.dom_ready');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var ajax = require('web.ajax');
    var _t = core._t;

    var inputSelector = "".concat(['text', 'password', 'email', 'url', 'tel', 'number', 'search', 'search-md'].map(function (selector) {
        return "input[type=".concat(selector, "]");
    }).join(', '), ", textarea");
    var textAreaSelector = '.materialize-textarea';

    var updateTextFields = function updateTextFields($input) {
        var $labelAndIcon = $input.siblings('label, i');
        var hasValue = $input.val().length;
        var hasPlaceholder = $input.attr('placeholder');
        var addOrRemove = "".concat(hasValue || hasPlaceholder ? 'add' : 'remove', "Class");
        $labelAndIcon[addOrRemove]('active');
    };


    $(inputSelector).each(function (index, input) {
        var $this = $(input);
        var $labelAndIcon = $this.siblings('label, i');
        updateTextFields($this);
        var isValid = input.validity.badInput;

        if (isValid) {
            $labelAndIcon.addClass('active');
        }
    });


    if ($.blockUI) {
        // our message needs to appear above the modal dialog
        $.blockUI.defaults.baseZ = 2147483647; //same z-index as StripeCheckout
        $.blockUI.defaults.css.border = '0';
        $.blockUI.defaults.css["background-color"] = '';
        $.blockUI.defaults.overlayCSS["opacity"] = '0.9';
    }

    var HandlingCalendarSummary = Widget.extend({
        events: {
            "click button#confirm-cancel": "cancel",
        },

        cancel: function (event) {
            event.preventDefault();
            if ($.blockUI) {
                var msg = _t("Please wait a second...");
                $.blockUI({
                    'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                        '    <br />' + msg +
                        '</h2>'
                });
                window.location.href = $(event.target).data('url') + '?access_token=' + $(event.target).data('access-token');
            }
        }
    })

    $("div[name='novobi_view']").each(function () {
        var state = this.dataset.eventState;
        if (state == 'closed') {
            $("a[role='button']").attr("style", "display:none;")
        }
    })

    $("div#appointment_controller").each(function () {
            var $el = $(this);
            var item = new HandlingCalendarSummary();
            item.attachTo($el)
        }
    )

})