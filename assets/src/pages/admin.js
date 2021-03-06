$( document ).ready( function() {
    $('div.suggest_name_wrapper button').click(function() {
        var fields = $(this).data('suggestFields').split(',');
        var sep = $(this).data('separator');
        if (!sep) {
            sep = "-"
        }
        var name = "";
        $.each(fields, function(i,field) {
            let input = $('#id_'+field);
            let field_name=input.val();
            if (input.parent().hasClass('autocomplete-light-widget')) {
                field_name=input.parent().find('.title').data('name');
                if (field_name){
                    field_name = field_name.trim();
                }
            }

            if (i==0) {
                name = field_name
            } else {
                name = name + sep + field_name;
            }
        })
        $(this).siblings('input').val(name);
        return false;
    });

    $('a').click(function() {
        if ($(this).attr('href')) {
            var url = $(this).attr('href').replace('django/admin','account/django')
            var title = $('title').text()

            top.window.history.pushState("", title, url);
        }
    });
});
