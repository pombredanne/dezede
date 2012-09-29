# coding: utf-8

from .functions import str_list, str_list_w_last, href, sc
from django.db.models import CharField, FloatField, BooleanField, ForeignKey, \
                             ManyToManyField, OneToOneField, permalink, \
                             get_model
from tinymce.models import HTMLField
from ..templatetags.extras import abbreviate
from django.utils.html import strip_tags
from django.utils.translation import pgettext, ungettext_lazy, \
                                     ugettext,  ugettext_lazy as _
from autoslug import AutoSlugField
from .common import CustomModel, LOWER_MSG, PLURAL_MSG, calc_pluriel


class Prenom(CustomModel):
    prenom = CharField(_(u'prénom'), max_length=100)
    classement = FloatField(_('classement'), default=1.0)
    favori = BooleanField(_('favori'), default=True)

    class Meta:
        verbose_name = ungettext_lazy(u'prénom', u'prénoms', 1)
        verbose_name_plural = ungettext_lazy(u'prénom', u'prénoms', 2)
        ordering = ['prenom', 'classement']
        app_label = 'catalogue'

    def __unicode__(self):
        return self.prenom

    @staticmethod
    def autocomplete_search_fields():
        return ('prenom__icontains',)


class TypeDeParenteDIndividus(CustomModel):
    nom = CharField(_('nom'), max_length=50, help_text=LOWER_MSG, unique=True)
    nom_pluriel = CharField(_('nom (au pluriel)'), max_length=55, blank=True,
        help_text=PLURAL_MSG)
    classement = FloatField(_('classement'), default=1.0)

    class Meta:
        verbose_name = ungettext_lazy(u'type de parenté d’individus',
                                      u'types de parenté d’individus', 1)
        verbose_name_plural = ungettext_lazy(
                u'type de parenté d’individus',
                u'types de parenté d’individus',
                2)
        ordering = ['classement']
        app_label = 'catalogue'

    def pluriel(self):
        return calc_pluriel(self)

    def __unicode__(self):
        return self.nom


class ParenteDIndividus(CustomModel):
    type = ForeignKey('TypeDeParenteDIndividus', related_name='parentes',
        verbose_name=_('type'))
    individus_cibles = ManyToManyField('Individu',
        related_name='enfances_cibles', verbose_name=_('individus cibles'))

    class Meta:
        verbose_name = ungettext_lazy(u'parenté d’individus',
                                      u'parentés d’individus', 1)
        verbose_name_plural = ungettext_lazy(u'parenté d’individus',
                                             u'parentés d’individus', 2)
        ordering = ['type']
        app_label = 'catalogue'

    def __unicode__(self):
        out = self.type.nom
        if self.individus_cibles.count() > 1:
            out = self.type.pluriel()
        out += ' :'
        cs = self.individus_cibles.iterator()
        out += str_list((unicode(c) for c in cs), ' ; ')
        return out


class Individu(CustomModel):
    particule_nom = CharField(_(u'particule du nom d’usage'), max_length=10,
        blank=True,)
    # TODO: rendre le champ nom 'blank'
    nom = CharField(_(u'nom d’usage'), max_length=200)
    particule_nom_naissance = CharField(_('particule du nom de naissance'),
        max_length=10, blank=True)
    nom_naissance = CharField(_('nom de naissance'), max_length=200,
        blank=True,
        help_text=_(u'Ne remplir que s’il est différent du nom d’usage.'))
    prenoms = ManyToManyField('Prenom', related_name='individus', blank=True,
        null=True, verbose_name=_(u'prénoms'))
    pseudonyme = CharField(_('pseudonyme'), max_length=200, blank=True)
    DESIGNATIONS = (
        ('S', _(u'Standard (nom, prénoms et pseudonyme)')),
        ('P', _('Pseudonyme (uniquement)')),
        ('L', _('Nom de famille (uniquement)')),  # L pour Last name
        ('B', _('Nom de naissance (standard)')),  # B pour Birth name
        ('F', _(u'Prénom(s) favori(s) (uniquement)')),  # F pour First name
    )
    designation = CharField(_(u'désignation'), max_length=1,
        choices=DESIGNATIONS, default='S')
    TITRES = (
        ('M', _('M.')),
        ('J', _('Mlle')),  # J pour Jouvencelle
        ('F', _('Mme')),
    )
    titre = CharField(pgettext('individu', 'titre'), max_length=1,
        choices=TITRES, blank=True)
    ancrage_naissance = OneToOneField('AncrageSpatioTemporel', blank=True,
        null=True, related_name='individus_nes',
        verbose_name=_(u'ancrage de naissance'))
    ancrage_deces = OneToOneField('AncrageSpatioTemporel', blank=True,
        null=True, related_name='individus_decedes',
        verbose_name=_(u'ancrage du décès'))
    ancrage_approx = OneToOneField('AncrageSpatioTemporel',
        blank=True, null=True,
        related_name='individus', verbose_name=_(u'ancrage approximatif'),
        help_text=_(u'Ne remplir que si on ne connaît aucune date précise.'))
    professions = ManyToManyField('Profession', related_name='individus',
        blank=True, null=True, verbose_name=_('professions'))
    parentes = ManyToManyField('ParenteDIndividus',
        related_name='individus_orig', blank=True, null=True,
        verbose_name=_(u'parentés'))
    biographie = HTMLField(_('biographie'), blank=True)
    illustrations = ManyToManyField('Illustration', related_name='individus',
        blank=True, null=True, verbose_name=_('illustrations'))
    documents = ManyToManyField('Document', related_name='individus',
        blank=True, null=True, verbose_name=_('documents'))
    etat = ForeignKey('Etat', related_name='individus', null=True, blank=True,
        verbose_name=_(u'état'))
    notes = HTMLField(_('notes'), blank=True)
    slug = AutoSlugField(populate_from=lambda s: unicode(s)
                                                       if not s.nom else s.nom)

    @permalink
    def get_absolute_url(self):
        return ('individu', [self.slug],)

    @permalink
    def permalien(self):
        return ('individu_pk', [self.pk])

    def link(self):
        return self.html()
    link.short_description = _('lien')
    link.allow_tags = True

    def oeuvres(self):
        pk_list = self.auteurs.values_list('oeuvres', flat=True) \
                                                    .order_by('oeuvres__titre')
        if pk_list:
            return get_model('catalogue',
                             'Oeuvre').objects.in_bulk(tuple(pk_list)).values()

    def publications(self):
        pk_list = self.auteurs.values_list('sources', flat=True)
        if pk_list:
            return get_model('catalogue',
                             'Source').objects.in_bulk(tuple(pk_list)).values()

    def apparitions(self):
        q = get_model('catalogue', 'Evenement').objects.none()
        els = get_model('catalogue', 'ElementDeProgramme').objects.none()
        for attribution in self.attributions_de_pupitre.iterator():
            els |= attribution.elements_de_programme.all()
        for el in els.distinct():
            q |= el.evenements.all()
        return q.distinct()

    def parents(self):
        pk_list = self.parentes.values_list('individus_cibles', flat=True) \
                                             .order_by('individus_cibles__nom')
        if pk_list:
            return Individu.objects.in_bulk(tuple(pk_list)).values()

    def enfants(self):
        pk_list = self.enfances_cibles.values_list('individus_orig',
                                     flat=True).order_by('individus_orig__nom')
        if pk_list:
            return Individu.objects.in_bulk(tuple(pk_list)).values()

    def calc_prenoms_methode(self, fav):
        if not self.pk:
            return ''
        prenoms = self.prenoms.order_by('classement', 'prenom')
        if fav:
            prenoms = (p for p in prenoms if p.favori)
        return ' '.join(unicode(p) for p in prenoms)

    def calc_prenoms(self):
        return self.calc_prenoms_methode(False)
    calc_prenoms.short_description = _(u'prénoms')
    calc_prenoms.admin_order_field = 'prenoms__prenom'

    def calc_fav_prenoms(self):
        return self.calc_prenoms_methode(True)

    def calc_titre(self, tags=False):
        titres = {}
        if tags:
            titres = {
                'M': ugettext('M.'),
                'J': ugettext('M<sup>lle</sup>'),
                'F': ugettext('M<sup>me</sup>'),
            }
        else:
            titres = {
                'M': ugettext('Monsieur'),
                'J': ugettext('Mademoiselle'),
                'F': ugettext('Madame'),
            }
        if self.titre:
            return titres[self.titre]
        return ''

    def get_particule(self, naissance=False, lon=True):
        particule = self.particule_nom_naissance if naissance \
               else self.particule_nom
        if lon and particule != u'' and particule[-1] not in ("'", u'’'):
            particule += ' '
        return particule

    def naissance(self):
        if self.ancrage_naissance:
            return unicode(self.ancrage_naissance)
        return ''

    def naissance_html(self, tags=True):
        if self.ancrage_naissance:
            return self.ancrage_naissance.short_html(tags)
        return ''

    def deces(self):
        if self.ancrage_deces:
            return unicode(self.ancrage_deces)
        return ''

    def deces_html(self, tags=True):
        if self.ancrage_deces:
            return self.ancrage_deces.short_html(tags)
        return ''

    def ancrage(self):
        if self.ancrage_approx:
            return unicode(self.ancrage_approx)
        return ''

    def calc_professions(self):
        if not self.pk:
            return ''
        ps = self.professions.iterator()
        titre = self.titre
        return str_list_w_last(p.gendered(titre) for p in ps)
    calc_professions.short_description = _('professions')
    calc_professions.admin_order_field = 'professions__nom'

    def html(self, tags=True, lon=False, prenoms_fav=True,
             force_standard=False, show_prenoms=True):
        def add_particule(nom, lon, correct_designation, naissance=False):
            particule = self.get_particule(naissance)
            if lon:
                nom = particule + nom
            return nom

        designation = self.designation
        titre = self.calc_titre(tags)
        prenoms = self.calc_prenoms_methode(prenoms_fav)
        nom = self.nom
        nom = add_particule(nom, lon, designation != 'B')
        pseudonyme = self.pseudonyme
        nom_naissance = self.nom_naissance
        nom_naissance = add_particule(nom_naissance, lon,
                                            designation == 'B', naissance=True)
        particule = self.get_particule(naissance=(designation == 'B'), lon=lon)

        def main_style(s):
            return sc(s, tags)

        def standard(main):
            l = []
            out = ''
            if nom and not prenoms:
                l.append(titre)
            l.append(main)
            if show_prenoms and (prenoms or particule and not lon):
                if lon:
                    l.insert(max(len(l) - 1, 0), prenoms)
                else:
                    s = str_list((abbreviate(prenoms), sc(particule, tags)),
                                 ' ')
                    l.append(u'(%s)' % s)
            out = str_list(l, ' ')
            if pseudonyme:
                alias = ugettext('dite') if self.titre in ('J', 'F',) \
                   else ugettext('dit')
                out += ugettext(u', %(alias)s %(pseudonyme)s') % \
                    {'alias': alias,
                     'pseudonyme': pseudonyme}
            return out

        main_choices = {
          'S': nom,
          'F': prenoms,
          'L': nom,
          'P': pseudonyme,
          'B': nom_naissance,
        }
        main = main_style(main_choices['S' if force_standard else designation])
        out = standard(main) if designation in ('S', 'B',) or force_standard \
              else main
        url = None if not tags else self.get_absolute_url()
        out = href(url, out, tags)
        return out
    html.short_description = _('rendu HTML')
    html.allow_tags = True

    def nom_seul(self, tags=False):
        return self.html(tags, False, show_prenoms=False)

    def nom_complet(self, tags=True, prenoms_fav=False, force_standard=True):
        return self.html(tags, True, prenoms_fav, force_standard)

    class Meta:
        verbose_name = ungettext_lazy('individu', 'individus', 1)
        verbose_name_plural = ungettext_lazy('individu', 'individus', 2)
        ordering = ['nom']
        app_label = 'catalogue'

    def __unicode__(self):
        return strip_tags(self.html(False))

    @staticmethod
    def autocomplete_search_fields():
        return (
            'nom__icontains',
            'nom_naissance__icontains',
            'pseudonyme__icontains',
            'prenoms__prenom__icontains',
        )