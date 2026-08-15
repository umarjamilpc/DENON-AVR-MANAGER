function buttonClickSetPwOnLevel() {
	surrParaFormSubmit();
}
function textPwOnLevel(zone) {
	if(zone == "Main") document.surrParaForm.setMainPwOnLevel.value = "on";
	surrParaFormSubmit();
}
function buttonClickDnPwOnLevel(zone) {
	if(zone == "Main") document.surrParaForm.setMainPwOnLevel.value = "<";
	surrParaFormSubmit();
}
function buttonClickUpPwOnLevel(zone) {
	if(zone == "Main") document.surrParaForm.setMainPwOnLevel.value = ">";
	surrParaFormSubmit();
}
function refreshHref() {
	location.href="r_audio.asp";
}
function radioBtn() {
	surrParaFormSubmit();
}
function textBoxLevel(level) {
	if(level == "EffectLevel"){
		document.surrParaForm.setEffectLevel.value = "on";
	}else if(level == "DelayTime"){
		document.surrParaForm.setDelayTime.value = "on";
	}else if(level == "LfeLevel"){
		document.surrParaForm.setLfeLevel.value = "on";
	}
	
	surrParaFormSubmit();
}

function listBox() {
	surrParaFormSubmit();
}
function checkBox() {
	surrParaFormSubmit();
}

function buttonClickDn(level) {
	if(level == "LfeLevel"){
		document.surrParaForm.setLfeLevel.value = "<";
		surrParaFormSubmit()
	}else if(level == "DelayTime"){
		document.surrParaForm.setDelayTime.value = "<";
		surrParaFormSubmit()
	}else if(level == "EffectLevel"){
		document.surrParaForm.setEffectLevel.value = "<";
		surrParaFormSubmit()
	}else if(level == "AudioDelay"){
		document.surrParaForm.setAudioDelay.value = "<";
		surrParaFormSubmit()
	}else if(level == "StageWidth"){
		surrParaFormSubmit()
	}else if(level == "StageHeight"){
		surrParaFormSubmit()
	}

}
function buttonClickUp(level) {
	if(level == "LfeLevel"){
		 document.surrParaForm.setLfeLevel.value = ">";
		 surrParaFormSubmit()
	}else if(level == "DelayTime"){
		document.surrParaForm.setDelayTime.value = ">";
		surrParaFormSubmit()
	}else if(level == "EffectLevel"){
		document.surrParaForm.setEffectLevel.value = ">";
		surrParaFormSubmit()
	}else if(level == "AudioDelay"){
		document.surrParaForm.setAudioDelay.value = ">";
		surrParaFormSubmit()
	}else if(level == "StageWidth"){
		surrParaFormSubmit()
	}else if(level == "StageHeight"){
		surrParaFormSubmit()
	}
}
function buttonClickSet(level) {

	if(level == "StageWidth"){
		surrParaFormSubmit()
	}else if(level == "StageHeight"){
		surrParaFormSubmit()

	}else if(level == "LfeLevel"){
		document.surrParaForm.setLfeLevel.value = "on";
		surrParaFormSubmit()

	}else if(level == "EffectLevel"){
		document.surrParaForm.setEffectLevel.value = "on";
		surrParaFormSubmit()

	}else if(level == "DelayTime"){
		document.surrParaForm.setDelayTime.value = "on";
		surrParaFormSubmit()

	}	
}

function buttonClickSetAudioDelay() {
	val = eval(document.surrParaForm.textAudioDelay.value);
	document.surrParaForm.setAudioDelay.value = "on";
	if(val>=0 && val<=200){
		surrParaFormSubmit();
	}
}

function buttonDefault() {
	document.surrParaForm.setSurrParaDefault.value = "Default";
	surrParaFormSubmit();
}

function surrParaFormSubmit() {
	document.surrParaForm.submit();
}
