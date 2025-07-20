	.section .text.initMouseKeyboard
initMouseKeyboard:
	jmp (%pc,afterInitMouseKeyboard)

	.section .text.afterInitMouseKeyboard
afterInitMouseKeyboard:	

	.section .text.detectKeyboard
detectKeyboard:	

	.section .text.detectKeyboardAfterUnknown
detectKeyboardAfterUnknown:
	jmp (%pc,afterDetectKeyboard)

	.section .text.afterDetectKeyboard
afterDetectKeyboard:
