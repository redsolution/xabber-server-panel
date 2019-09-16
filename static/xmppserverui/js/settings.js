function onSaveConfig() {
    $.post( "/server/settings/save/", function( data ) {
      $( "#result" ).html( data );
    });
}