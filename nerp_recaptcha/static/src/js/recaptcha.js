odoo.define('nerp_frontend.recaptcha', function (require) {
    "use strict";

    require('web.dom_ready');
    var Widget = require('web.Widget');
    var ajax = require('web.ajax');
    var Recaptchav3 = Widget.extend({
        init: function (obj) {
            ajax.jsonRpc(
                '/recaptchav3/site_key', 'call',
            ).then(function (vals) {
                if (vals['success']){
                    var site_key = vals['site_key']
                    $.ajax({
                        url: 'https://www.google.com/recaptcha/api.js?render=' + site_key,
                        dataType: "script",
                        cache: true,
                    }).done(function () {
                        if (vals['site_key']) {
                            grecaptcha.ready(function () {
                                grecaptcha.execute(site_key, {action: 'submit_form'}).then(function (token) {
                                    obj.append('<input class=" d-none" name="g-recaptcha-response" value="' + token + '"/>')
                                });
                            });
                        }
                    })
                } else {
                    console.log(vals['error'])
                }
            })
            obj.append('<input type="hidden" name="recaptcha" value="1"/>')
        }
    });

    $(".custom-website-recaptchav3").each(function () {
            var $el = $(this);
            var item = new Recaptchav3($el);
            item.attachTo($el)
        }
    )
})
