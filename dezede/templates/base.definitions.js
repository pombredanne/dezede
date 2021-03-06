{# Gestion des tooltips #}
get_tooltips_options = function() {
  return {
    placement: 'top',
    container: 'body'
  };
};

get_tooltips = function() {
  return $('*[title], *[data-original-title]');
};
tooltips_disable = function() {
  $.cookie("tooltips_enabled", "false", {path: '/'});
  get_tooltips().tooltip('destroy');
};
tooltips_enable = function() {
  $.cookie("tooltips_enabled", "true", {path: '/'});
  get_tooltips().tooltip(get_tooltips_options());
};

tooltips_reload = function() {
  var tooltips_enabled = $.cookie("tooltips_enabled");
  tooltips_enable();
  if(tooltips_enabled == "false") {
    tooltips_disable();
  }
};
{# Fin de la gestion des tooltips #}

{# Google Analytics #}
var _gaq = _gaq || [];
_gaq.push(['_setAccount', 'UA-37152824-1']);
_gaq.push(['_setDomainName', 'dezede.org']);
_gaq.push(['_trackPageview']);

(function() {
  var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
  ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
  var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
})();
{# Fin de Google Analytics #}
