odoo.define('website_calendar.event_url', function (require) {
    'use strict';

    var AbstractField = require('web.AbstractField');
    var core = require('web.core');
    var fieldRegistry = require('web.field_registry');

    var _t = core._t;

    var FieldEmployeeUrl = AbstractField.extend({
        events: _.extend({}, AbstractField.prototype.events, {
            'click .o_website_calendar_copy_icon': '_stopPropagation',
            'click .o_form_uri': '_stopPropagation',
        }),
        supportedFieldTypes: [],
        init: function () {
            this._super.apply(this, arguments);
            this.tagName = 'div';

            this.url = false;
            var work_email = this.record.data['work_email'];
            var unique_name = work_email.match(/^([^@]*)@/)[1];
            var personal_meeting_path = this.record.getContext({fieldName: 'id'}).personal_meeting_path;
            var event_token = this.record.getContext({fieldName: 'id'}).appointment_type_website_token;

            if (unique_name) {
                this.url = 'https://' + personal_meeting_path + '/booking/appointment/calendar?event_token='+event_token+'&employee=' + unique_name;
            }
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * The widget needs to be a link with proper href and a clipboard
         * icon that saves the url to the clipboard, classes are added for
         * proper design.
         *
         * @override
         * @private
         */
        _render: function () {
            this._super.apply(this, arguments);
            if (!this.url) {
                return;
            }
            var $link = $('<a>', {
                class: 'o_form_uri fa-o_text_overflow',
                href: this.url,
                text: this.url,
            });
            var $icon = $('<div>', {
                class: 'fa fa-clipboard o_website_calendar_copy_icon'
            });

            $icon.tooltip({title: _t("Copied !"), trigger: "manual", placement: "right"});
            var clipboard = new window.ClipboardJS($icon[0], {
                text: this.url.trim.bind(this.url),
            });
            clipboard.on("success", function (e) {
                _.defer(function () {
                    $icon.tooltip("show");
                    _.delay(function () {
                        $icon.tooltip("hide");
                    }, 800);
                });
            });

            this.$el.empty()
                .append($link)
                .append($icon);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Stop the propagation of the event.
         * On this widget, clicks should only open a link or copy the url to the
         * clipboard. Prevent the opening of the form view if in a list view.
         *
         * @private
         * @param {MouseEvent} event
         */
        _stopPropagation: function (ev) {
            ev.stopPropagation();
        },
    });

    var FormUrl = AbstractField.extend({
        events: _.extend({}, AbstractField.prototype.events, {
            'click .o_website_calendar_copy_icon': '_stopPropagation',
            'click .o_form_uri': '_stopPropagation',
        }),

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * The widget needs to be a link with proper href and a clipboard
         * icon that saves the url to the clipboard, classes are added for
         * proper design.
         *
         * @override
         * @private
         */
        _render: function () {
            var result = this._super.apply(this, arguments);
            console.log(this);
            if (!this.value) {
                return result;
            }
            var $link = $('<a>', {
                class: 'o_form_uri fa-o_text_overflow',
                href: this.value,
                text: this.value,
            });
            var $icon = $('<div>', {
                class: 'fa fa-clipboard o_website_calendar_copy_icon'
            });

            $icon.tooltip({title: _t("Copied !"), trigger: "manual", placement: "right"});
            var clipboard = new window.ClipboardJS($icon[0], {
                text: this.value.trim.bind(this.value),
            });
            clipboard.on("success", function (e) {
                _.defer(function () {
                    $icon.tooltip("show");
                    _.delay(function () {
                        $icon.tooltip("hide");
                    }, 800);
                });
            });

            this.$el.empty()
                .append($link)
                .append($icon);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Stop the propagation of the event.
         * On this widget, clicks should only open a link or copy the url to the
         * clipboard. Prevent the opening of the form view if in a list view.
         *
         * @private
         * @param {MouseEvent} event
         */
        _stopPropagation: function (ev) {
            ev.stopPropagation();
        },
    });

    fieldRegistry.add('form_url', FormUrl)
    fieldRegistry.add('employee_url', FieldEmployeeUrl)
});
