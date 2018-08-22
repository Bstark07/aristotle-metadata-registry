$(document).ready(function() {

  var item_id;
  var button;
  var message_p = $('#modal-message')
  var csrftoken = $("[name=csrfmiddlewaretoken]").val(); // Can do this since a token is already on the page

  // Remove href attributes if javascript enabled
  // This will not be needed if using bootstrap 4.0
  $('.delete-button').each(function() {
      $(this).removeAttr('href');
  })

  $('#delete-modal').on('show.bs.modal', function(event) {
    button = $(event.relatedTarget);
    var modal=$(this);
    // Extract info from data-* attributes
    item_id = button.data('item-id') 
    var item_name = button.data('item-name') 
    console.log(item_id)
    message_p.html('Are you sure you want to delete ' + item_name + '?')
  })

  $('#delete-confirm-button').click(function() {
    $.ajax({
      method: "POST",
      url: delete_submit_url,
      data: {item: item_id, csrfmiddlewaretoken: csrftoken},
      datatype: "json",
      success: function(data) {
          if (data.completed) {
            // Remove item's row
            button.closest('tr').remove();
            $('#delete-modal').modal('hide');
          } else if (data.message) {
            message_p.html(data.message);
          }
      },
      error: function() {
          message_p.html("The item could not be deleted");
      }
    })
  })

  function disable_check(widget) {
    var count = widget.find('.form-group').length
    var button = widget.find('.remove-field').first()
    if (count == 1) {
      button.prop('disabled', true)
    } else if (count > 1) {
      button.prop('disabled', false)
    }
  }

  function remove_field(button) {
    var widget = $(button).closest('.multi-widget')
    $(button).closest('.form-group').remove()
    disable_check(widget)
  }

  function add_field(button) {
    var widget = $(button).closest('.multi-widget')
    var fields = widget.find('.multi-fields').first()
    var clone = fields.find('.form-group').first().clone()
    var button = clone.find('.remove-field').first()
    
    button.prop('disabled', false)
    button.click(function() {
      remove_field(this)
    })

    clone.find('input').val('')
    clone.appendTo(fields)
    disable_check(widget)
  }

  $('.add-field').click(function() {
    add_field(this);
  })

  $('.remove-field').click(function() {
    remove_field(this);
  })

  $('.multi-widget').each(function() {
    var widget = $(this)
    disable_check(widget)
  })

})
