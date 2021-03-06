# coding: utf-8

from __future__ import unicode_literals
from django.contrib.contenttypes.generic import GenericRelation
from django.db.models import CharField, DateField, ForeignKey, \
                             ManyToManyField, permalink, PROTECT
from django.utils.encoding import python_2_unicode_compatible
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.translation import ungettext_lazy
from tinymce.models import HTMLField
from cache_tools import cached_ugettext as ugettext, cached_ugettext_lazy as _
from .common import CommonModel, AutoriteModel, LOWER_MSG, PLURAL_MSG, \
                    DATE_MSG, calc_pluriel, SlugModel
from .functions import ex, cite, no as no_func, date_html as date_html_func, \
    href, small, str_list


__all__ = (b'TypeDeSource', b'Source')


@python_2_unicode_compatible
class TypeDeSource(CommonModel, SlugModel):
    nom = CharField(_('nom'), max_length=200, help_text=LOWER_MSG, unique=True,
                    db_index=True)
    nom_pluriel = CharField(_('nom (au pluriel)'), max_length=230, blank=True,
                            db_index=True, help_text=PLURAL_MSG)

    class Meta(object):
        verbose_name = ungettext_lazy('type de source', 'types de source', 1)
        verbose_name_plural = ungettext_lazy('type de source',
                                             'types de source', 2)
        ordering = ('slug',)
        app_label = 'libretto'

    @staticmethod
    def invalidated_relations_when_saved(all_relations=False):
        if all_relations:
            return ('sources',)
        return ()

    def pluriel(self):
        return calc_pluriel(self)

    def __str__(self):
        return self.nom


@python_2_unicode_compatible
class Source(AutoriteModel):
    # TODO: Rendre les sources polymorphes.  On trouve des périodiques, mais
    # également des registres, des catalogues, etc.
    nom = CharField(_('nom'), max_length=200, db_index=True,
                    help_text=ex(_('Journal de Rouen')))
    numero = CharField(_('numéro'), max_length=50, blank=True, db_index=True,
                       help_text=_('Sans « № »') + '. ' + ex('52'))
    date = DateField(_('date'), db_index=True, help_text=DATE_MSG,
                     null=True, blank=True)
    page = CharField(_('page'), max_length=50, blank=True,
                     help_text=_('Sans « p. »') + '. ' + ex('3'))
    type = ForeignKey('TypeDeSource', related_name='sources', db_index=True,
                      help_text=ex(_('compte rendu')), verbose_name=_('type'),
                      on_delete=PROTECT)
    contenu = HTMLField(_('contenu'), blank=True,
        help_text=_('Recopié tel quel, avec les fautes d’orthographe suivies '
                    'de « [<em>sic</em>] » le cas échéant.'))
    auteurs = GenericRelation('Auteur')
    # TODO: Permettre les sources d'autres données que des événements :
    # œuvres, lieux, individus, etc.
    evenements = ManyToManyField('Evenement', related_name='sources',
        blank=True, null=True, db_index=True, verbose_name=_('événements'))

    class Meta(object):
        verbose_name = ungettext_lazy('source', 'sources', 1)
        verbose_name_plural = ungettext_lazy('source', 'sources', 2)
        ordering = ('date', 'nom', 'numero', 'page', 'type')
        app_label = 'libretto'
        permissions = (('can_change_status', _('Peut changer l’état')),)

    def __str__(self):
        return strip_tags(self.html(False))

    @permalink
    def get_absolute_url(self):
        return b'source_permanent_detail', (self.pk,)

    def permalien(self):
        return self.get_absolute_url()

    def link(self):
        return self.html()
    link.short_description = _('Lien')
    link.allow_tags = True

    def auteurs_html(self, tags=True):
        return self.auteurs.html(tags)

    def date_html(self, tags=True):
        return date_html_func(self.date, tags)

    def no(self):
        return no_func(self.numero)

    def p(self):
        return ugettext('p. %s') % self.page

    def html(self, tags=True, pretty_title=False):
        url = None if not tags else self.get_absolute_url()
        l = [cite(self.nom, tags)]
        if self.numero:
            l.append(self.no())
        if self.date:
            l.append(self.date_html(tags))
        if self.page:
            l.append(self.p())
        l = (l[0], small(str_list(l[1:]), tags=tags)) if pretty_title else l
        out = str_list(l)
        return mark_safe(href(url, out, tags))
    html.short_description = _('rendu HTML')
    html.allow_tags = True

    def pretty_title(self):
        return self.html(pretty_title=True)

    def has_events(self):
        return self.evenements.exists()
    has_events.short_description = _('Événements')
    has_events.boolean = True
    has_events.admin_order_field = 'evenements'

    def has_program(self):
        evenements = self.evenements.all()
        if not evenements:
            return False
        for e in evenements:
            if not e.has_program():
                return False
        return True
    has_program.short_description = _('Programme')
    has_program.boolean = True
