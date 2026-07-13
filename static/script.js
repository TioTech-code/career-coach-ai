document.addEventListener("DOMContentLoaded",()=>{

const forms=document.querySelectorAll("form");

forms.forEach(form=>{

form.addEventListener("submit",()=>{

document.body.insertAdjacentHTML(

"beforeend",

`

<div id="loading-screen">

<div class="loader"></div>

<h2>AI is analysing your application...</h2>

</div>

`

);

});

});

});