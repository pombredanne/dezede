# coding: utf-8

from __future__ import unicode_literals
import datetime
from django.core.exceptions import ValidationError
from django.db.models import CharField, ForeignKey, BooleanField, \
                             DateField, TimeField, permalink, Q, PROTECT
from django.template.defaultfilters import time
from django.utils.encoding import python_2_unicode_compatible, smart_text, \
    force_text
from django.utils.html import strip_tags
from django.utils.translation import ungettext_lazy
from polymorphic_tree.managers import PolymorphicMPTTQuerySet, \
    PolymorphicMPTTModelManager
from polymorphic_tree.models import PolymorphicMPTTModel, \
    PolymorphicTreeForeignKey
from tinymce.models import HTMLField
from cache_tools import cached_ugettext as ugettext, \
    cached_pgettext as pgettext, cached_ugettext_lazy as _
from .common import CommonModel, AutoriteModel, LOWER_MSG, PLURAL_MSG, \
                    PublishedManager, DATE_MSG, calc_pluriel, SlugModel, \
                    UniqueSlugModel, PublishedQuerySet, CommonTreeQuerySet, \
    CommonTreeManager
from .evenement import Evenement
from .functions import capfirst, href, date_html, str_list, ex
from .individu import Individu
from .oeuvre import Oeuvre


__all__ = (
    b'NatureDeLieu', b'Lieu', b'LieuDivers', b'Institution', b'Saison',
    b'AncrageSpatioTemporel'
)


@python_2_unicode_compatible
class NatureDeLieu(CommonModel, SlugModel):
    nom = CharField(_('nom'), max_length=255, help_text=LOWER_MSG, unique=True,
                    db_index=True)
    nom_pluriel = CharField(_('nom (au pluriel)'), max_length=430, blank=True,
                            help_text=PLURAL_MSG)
    referent = BooleanField(_('référent'), default=False, db_index=True,
        help_text=_('L’affichage d’un lieu remonte jusqu’au lieu référent.') \
        + ' ' \
        + ex(force_text(_('ville, institution, salle')),
             pre=force_text(_('dans une architecture de pays, villes, théâtres, '
                           'etc, ')),
             post=force_text(_(' sera affiché car on remonte jusqu’à un lieu '
                            'référent, ici choisi comme étant ceux de nature '
                            '« ville »'))))

    class Meta(object):
        verbose_name = ungettext_lazy('nature de lieu', 'natures de lieu', 1)
        verbose_name_plural = ungettext_lazy('nature de lieu',
                                             'natures de lieu', 2)
        ordering = ('slug',)
        app_label = 'libretto'

    @staticmethod
    def invalidated_relations_when_saved(all_relations=False):
        if all_relations:
            return ('lieux',)
        return ()

    def pluriel(self):
        return calc_pluriel(self)

    def __str__(self):
        return self.nom

    @staticmethod
    def autocomplete_search_fields():
        return 'nom__icontains',


class LieuQuerySet(PolymorphicMPTTQuerySet, PublishedQuerySet,
                   CommonTreeQuerySet):
    pass


class LieuManager(CommonTreeManager, PolymorphicMPTTModelManager,
                  PublishedManager):
    queryset_class = LieuQuerySet


@python_2_unicode_compatible
class Lieu(PolymorphicMPTTModel, AutoriteModel, UniqueSlugModel):
    nom = CharField(_('nom'), max_length=200, db_index=True)
    parent = PolymorphicTreeForeignKey(
        'self', null=True, blank=True, db_index=True, related_name='enfants',
        verbose_name=_('parent'))
    nature = ForeignKey(NatureDeLieu, related_name='lieux', db_index=True,
                        verbose_name=_('nature'), on_delete=PROTECT)
    # TODO: Parentés d'institution avec périodes d'activité pour l'histoire des
    # institutions.
    historique = HTMLField(_('historique'), blank=True)

    objects = LieuManager()

    class MPTTMeta(object):
        order_insertion_by = ('nom',)

    class Meta(object):
        verbose_name = ungettext_lazy('lieu ou institution',
                                      'lieux et institutions', 1)
        verbose_name_plural = ungettext_lazy('lieu ou institution',
                                             'lieux et institutions', 2)
        ordering = ('nom',)
        app_label = 'libretto'
        unique_together = ('nom', 'parent',)
        permissions = (('can_change_status', _('Peut changer l’état')),)

    @staticmethod
    def invalidated_relations_when_saved(all_relations=False):
        relations = ('get_real_instance',)
        if all_relations:
            relations += ('enfants', 'saisons', 'ancrages',
                    'dossiers',)
        return relations

    @permalink
    def get_absolute_url(self):
        return b'lieu_detail', [self.slug]

    @permalink
    def permalien(self):
        return b'lieu_permanent_detail', [self.pk]

    def link(self):
        return self.html()
    link.short_description = _('lien')
    link.allow_tags = True

    def get_slug(self):
        return self.nom

    def short_link(self):
        return self.html(short=True)

    def evenements(self):
        qs = self.get_descendants(include_self=True)
        return Evenement.objects.filter(
            Q(ancrage_debut__lieu__in=qs) | Q(ancrage_fin__lieu__in=qs))

    def individus_nes(self):
        return Individu.objects.filter(
            ancrage_naissance__lieu__in=self.get_descendants(include_self=True)
        ).order_by(*Individu._meta.ordering)

    def individus_decedes(self):
        return Individu.objects.filter(
            ancrage_deces__lieu__in=self.get_descendants(include_self=True)
        ).order_by(*Individu._meta.ordering)

    def oeuvres_creees(self):
        return Oeuvre.objects.filter(
            ancrage_creation__lieu__in=self.get_descendants(include_self=True)
        ).order_by(*Oeuvre._meta.ordering)

    def html(self, tags=True, short=False):
        if short or self.parent is None or self.nature.referent:
            out = self.nom
        else:
            ancestors = self.get_ancestors(include_self=True)
            l = list(ancestors.values_list('nom', 'nature__referent'))
            m = len(l) - 1
            out = ', '.join([nom for i, (nom, ref)
                             in enumerate(l) if not l[min(i + 1, m)][1]])

        url = None if not tags else self.get_absolute_url()
        return href(url, out, tags)
    html.short_description = _('rendu HTML')
    html.allow_tags = True

    def clean(self):
        if self.parent == self:
            raise ValidationError(_('Le lieu a une parenté avec lui-même.'))

    def __str__(self):
        return strip_tags(self.html(False))

    @staticmethod
    def autocomplete_search_fields():
        return ('nom__icontains',
                'parent__nom__icontains')


class LieuDivers(Lieu):
    # TODO: Stocker les codes postaux ?

    class Meta(object):
        verbose_name = ungettext_lazy('lieu', 'lieux', 1)
        verbose_name_plural = ungettext_lazy('lieu', 'lieux', 2)
        app_label = 'libretto'

    @staticmethod
    def invalidated_relations_when_saved(all_relations=False):
        return ('lieu_ptr',)


class Institution(Lieu):
    class Meta(object):
        verbose_name = ungettext_lazy('institution', 'institutions', 1)
        verbose_name_plural = ungettext_lazy('institution', 'institutions', 2)
        app_label = 'libretto'

    @staticmethod
    def invalidated_relations_when_saved(all_relations=False):
        return ('lieu_ptr',)


@python_2_unicode_compatible
class Saison(CommonModel):
    # TODO: Permettre de faire des saisons d'ensemble et non seulement de lieu.
    lieu = ForeignKey('Lieu', related_name='saisons',
                      verbose_name=_('lieu ou institution'))
    debut = DateField(_('début'), help_text=DATE_MSG)
    fin = DateField(_('fin'))

    class Meta(object):
        verbose_name = ungettext_lazy('saison', 'saisons', 1)
        verbose_name_plural = ungettext_lazy('saison', 'saisons', 2)
        ordering = ('lieu', 'debut')
        app_label = 'libretto'

    def __str__(self):
        d = {
            'lieu': smart_text(self.lieu),
            'debut': self.debut.year,
            'fin': self.fin.year
        }
        return pgettext('saison : pattern d’affichage',
                        '%(lieu)s, %(debut)d–%(fin)d') % d


@python_2_unicode_compatible
class AncrageSpatioTemporel(CommonModel):
    date = DateField(_('date (précise)'), blank=True, null=True, db_index=True,
        help_text=DATE_MSG)
    heure = TimeField(_('heure (précise)'), blank=True, null=True,
        db_index=True)
    lieu = ForeignKey('Lieu', related_name='ancrages', blank=True, null=True,
        db_index=True,
        verbose_name=_('lieu ou institution (précis)'))
    date_approx = CharField(_('date (approximative)'), max_length=200,
        blank=True, db_index=True,
        help_text=_('Ne remplir que si la date est imprécise.'))
    heure_approx = CharField(_('heure (approximative)'), max_length=200,
        blank=True, db_index=True,
        help_text=_('Ne remplir que si l’heure est imprécise.'))
    lieu_approx = CharField(_('lieu ou institution (approximatif)'),
        max_length=200, blank=True, db_index=True,
        help_text=_('Ne remplir que si le lieu (ou institution) est '
                    'imprécis(e).'))

    class Meta(object):
        verbose_name = ungettext_lazy('ancrage spatio-temporel',
                                      'ancrages spatio-temporels', 1)
        verbose_name_plural = ungettext_lazy('ancrage spatio-temporel',
                                             'ancrages spatio-temporels', 2)
        ordering = ('date', 'heure', 'lieu__parent', 'lieu', 'date_approx',
                    'heure_approx', 'lieu_approx')
        app_label = 'libretto'

    @staticmethod
    def invalidated_relations_when_saved(all_relations=False):
        if all_relations:
            return ('individus_nes', 'individus_decedes', 'individus',
                    'evenements_debuts', 'evenements_fins', 'oeuvres_creees',)
        return ()

    def year(self):
        if self.date:
            return self.date.year

    def month(self):
        if self.date:
            return self.date.month

    def day(self):
        if self.date:
            return self.date.day

    def calc_date(self, tags=True, short=False):
        if self.date_approx:
            return self.date_approx
        return date_html(self.date, tags, short)
    calc_date.short_description = _('date')
    calc_date.admin_order_field = 'date'

    def calc_heure(self):
        if self.heure:
            return time(self.heure, ugettext('H\hi'))
        return self.heure_approx
    calc_heure.short_description = _('heure')
    calc_heure.admin_order_field = 'heure'

    def calc_moment(self, tags=True, short=False):
        l = []
        date = self.calc_date(tags, short)
        heure = self.calc_heure()
        pat_date = ugettext('%(date)s') if self.date \
              else ugettext('%(date)s')
        pat_heure = ugettext('à %(heure)s') if self.heure \
               else ugettext('%(heure)s')
        l.append(pat_date % {'date': date})
        l.append(pat_heure % {'heure': heure})
        return str_list(l, ' ')

    def calc_lieu(self, tags=True, short=False):
        if self.lieu:
            return self.lieu.html(tags, short)
        return self.lieu_approx
    calc_lieu.short_description = _('lieu ou institution')
    calc_lieu.admin_order_field = 'lieu'
    calc_lieu.allow_tags = True

    def isoformat(self):
        if not self.date:
            return
        if self.heure:
            return datetime.datetime.combine(self.date, self.heure).isoformat()
        return self.date.isoformat()

    def html(self, tags=True, short=False):
        out = str_list((self.calc_lieu(tags, short),
                        self.calc_moment(tags, short)))
        return capfirst(out)

    def short_html(self, tags=True):
        return self.html(tags, short=True)

    def related_label(self):
        return self.get_change_link()

    @permalink
    def get_change_url(self):
        return 'admin:libretto_ancragespatiotemporel_change', (self.pk,)

    def get_change_link(self):
        return href(self.get_change_url(), smart_text(self), new_tab=True)

    def clean(self):
        if not (self.date or self.date_approx or self.lieu
                                              or self.lieu_approx):
            raise ValidationError(_('Il faut au moins une date ou un lieu '
                                    '(ils peuvent n’être qu’approximatifs)'))

    def __str__(self):
        return strip_tags(self.html(tags=False, short=True))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        cmp_fields = ('lieu', 'lieu_approx', 'date', 'date_approx',
                      'heure', 'heure_approx')
        for field in cmp_fields:
            if getattr(self, field) != getattr(other, field):
                return False
        return True

    def has_date(self):
        return self.date or self.date_approx

    def has_lieu(self):
        return self.lieu or self.lieu_approx

    def get_preciseness(self):
        score = 0
        for k in ('date', 'date_approx', 'lieu', 'lieu_approx'):
            if getattr(self, k):
                score += 1 if '_approx' in k else 2
        return score

    def is_more_precise_than(self, other):
        if other.__class__ is not self.__class__:
            return False

        if self.get_preciseness() > other.get_preciseness():
            return True
        return False

    @staticmethod
    def autocomplete_search_fields():
        return (
            'lieu__nom__icontains', 'lieu__parent__nom__icontains',
            'date__icontains', 'heure__icontains',
            'lieu_approx__icontains', 'date_approx__icontains',
            'heure_approx__icontains',
        )
