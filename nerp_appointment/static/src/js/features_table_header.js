odoo.define('website.fix_table_header', function (require) {
    'use strict';
    require('web.dom_ready');
    (function () {
         $(window).scroll(function () {
             $('div#wrapwrap').css('overflow-x', 'visible')
             var table_head_pos = $('header.o_affix_enabled').offset().top + $('header.o_affix_enabled').height()
             $('#managerial_head').css('top', table_head_pos)
             var table_head_pos = table_head_pos + $('#managerial_head').height()
             $('#financial_head').css('top', table_head_pos)
         })
    })();
    // $("header").append(`
    // <div id="moved_acounting_head" class="container">
    //                         <div class="row">
    //                             <table class="table table-bordered">
    //                                 <tbody>
    //                                     <tr>
    //                                         <td class="bg-epsilon">
    //                                             <h4>
    //                                                 <b>
    //                                                     <h4>
    //                                                         <b>Feature
    //                                                         </b>
    //                                                     </h4>
    //                                                 </b>
    //                                             </h4>
    //                                         </td>
    //                                         <td class="bg-epsilon">
    //                                             <h4>
    //                                                 <b>New Feature by Novobi
    //                                                 </b>
    //                                             </h4>
    //                                         </td>
    //                                         <td class="bg-epsilon">
    //                                             <h4>
    //                                                 <b>Enhanced Feature by Novobi
    //                                                 </b>
    //                                             </h4>
    //                                         </td>
    //                                     </tr>
    //                                     <tr>
    //                                         <td style="background-color: rgb(156, 156, 148);">
    //                                             <font style="color: rgb(255, 255, 255);">
    //                                                 <h4>Managerial Accounting
    //                                                 </h4>
    //                                             </font>
    //                                         </td>
    //                                         <td style="background-color: rgb(156, 156, 148);">
    //                                             <br>
    //                                         </td>
    //                                         <td style="background-color: rgb(156, 156, 148);">
    //                                             <br>
    //                                         </td>
    //                                     </tr>
    //                                 </tbody>
    //                             </table>
    //                         </div>
    //                     </div>
    // `)
    // var moved_table_head = $("header div#moved_acounting_head");
    // var table_head = $("table#accounting_head");
    // table_head.on("scroll", function () {
    //     if (table_head.offset().top < 0 && table_head.offset().bottom < 0) {
    //         moved_table_head.show()
    //         table_head.hide()
    //     } else {
    //         moved_table_head.hide()
    //         table_head.show()
    //     }
    // })
});
