(function() {
    $('form :input:visible:enabled:first').focus()

    var clipboard = new Clipboard('.button');

    clipboard.on('success', function(e) {
        e.trigger.innerHTML = "Copied!"
    });

    clipboard.on('error', function(e) {});
})();
