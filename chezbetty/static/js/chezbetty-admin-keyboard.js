
function attach_keypad () {
	if (onscreen_keyboard) {
		$("input:text, input:password, #login-uniqname").not(".numeric").keyboard({ 
		  layout : 'qwerty'
		});

		$("input.numeric:text").keyboard({ 
		  layout: "num",
		  restrictInput: true, // Prevent keys not in the displayed keyboard from being typed in
		  autoAccept: true
		});
	}
}

// Call at page load
attach_keypad();
