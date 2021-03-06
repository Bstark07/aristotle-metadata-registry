/* globals CKEDITOR */
import 'ckeditor/ckeditor.js'
import { addPlugins } from 'src/lib/ckeditor_plugins.js'
addPlugins(CKEDITOR)

export function initCKEditor() {
    $('textarea[data-type=ckeditortype]').each(function() {
        var textarea = $(this)
        var processed = textarea.attr('data-processed')
        if (processed == 0) {
            var config = JSON.parse(textarea.attr('data-config'));
            CKEDITOR.replace(this.id, config)
            textarea.attr('data-processed', 1)
        }
    })
}
