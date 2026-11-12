"""Pure validation and profile image generation."""
import io
import re
from PIL import Image, ImageDraw, ImageOps, ImageColor

CATALOG = {"Nova SBE — prototype catalog": ["Financial Modeling", "Corporate Finance", "Investments"]}
LANGUAGES = ["English", "Portuguese", "German", "Spanish", "French", "Italian", "Dutch", "Mandarin", "Arabic", "Hindi"]
SKIN = {"Light": "#F4C7A5", "Medium": "#C78F67", "Deep": "#714B37", "Blue": "#6EA9EB", "Green": "#75C5A0", "Purple": "#B394E8", "Pink": "#ED9BC0", "Gold": "#E5BD60"}
HAIR_COLORS = {"Brown": "#50382F", "Black": "#252431", "Blonde": "#D9B86D", "Red": "#AC5140", "Silver": "#BBC0D0"}
CLOTHES = {"Indigo": "#6370DB", "Green": "#319C84", "Coral": "#E67B72", "Gold": "#D1AB48"}
DEFAULT_AVATAR = dict(skin="Medium", hair="Short", hair_color="Brown", clothing="Indigo", accessory="None")
OPTIONS = dict(skin=list(SKIN), hair=["Short","Long","Curly","Bald","Bob","Ponytail","Bun","Mohawk","Spiky","Side swept"], hair_color=list(HAIR_COLORS),
               clothing=list(CLOTHES), accessory=["None","Glasses","Hat","Sunglasses","Headphones","Earrings","Headband","Bow","Crown","Scarf","Monocle"])

def validate_email(email):
    email=email.strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Enter a valid email address.")
    return email

def validate_username(username):
    username=username.strip()
    if not re.fullmatch(r"[A-Za-z0-9_]{3,24}",username):
        raise ValueError("Use 3–24 letters, numbers or underscores for your username.")
    return username

DEGREES = ["Not specified", "Bachelor's", "Master's", "Doctorate", "Associate", "Diploma / certificate", "Other"]

def validate_profile(username,university,courses,languages,avatar,degree="Not specified",area="",graduation_year=None):
    if graduation_year is not None and (type(graduation_year) is not int or not 2000<=graduation_year<=2100):
        raise ValueError("Enter an expected graduation year between 2000 and 2100.")
    username=validate_username(username)
    university=" ".join(university.split())
    if not 2<=len(university)<=160: raise ValueError("Enter a university name between 2 and 160 characters.")
    if not courses or len(courses)>50 or any(not isinstance(c,str) or not c.strip() or len(c.strip())>120 for c in courses):
        raise ValueError("Choose or enter at least one course (up to 120 characters each).")
    courses=list({c.strip().casefold():c.strip() for c in courses}.values())
    if degree not in DEGREES: raise ValueError("Choose a degree level.")
    area=area.strip()
    if len(area)>120: raise ValueError("Keep your field of study under 120 characters.")
    if not languages or not set(languages)<=set(LANGUAGES):
        raise ValueError("Choose at least one language.")
    if set(avatar)!=set(OPTIONS) or any(v not in OPTIONS[k] for k,v in avatar.items()):
        raise ValueError("Choose valid avatar options.")
    return dict(username=username,university=university,courses=list(dict.fromkeys(courses)),
                languages=list(dict.fromkeys(languages)),avatar=dict(avatar),degree=degree,area=area,graduation_year=graduation_year)

class _SmoothDraw:
    """Draw original design coordinates at 4x resolution for clean curved edges."""
    def __init__(self,image):self.draw=ImageDraw.Draw(image)
    def __getattr__(self,name):
        method=getattr(self.draw,name)
        def draw(coords,*args,**kwargs):
            def scale(value):
                return tuple(scale(v) for v in value) if isinstance(value,(tuple,list)) else value*4
            for key in ("width","radius"):
                if key in kwargs:kwargs[key]*=4
            return method(scale(coords),*args,**kwargs)
        return draw

def _tint(color,target,amount):
    base=ImageColor.getrgb(color);other=ImageColor.getrgb(target)
    return tuple(round(a+(b-a)*amount) for a,b in zip(base,other))

def render_avatar(settings):
    if set(settings)!=set(OPTIONS) or any(v not in OPTIONS[k] for k,v in settings.items()):
        raise ValueError("Invalid avatar settings.")
    # Keep the character separate from its theme-aware CSS backdrop.
    im=Image.new("RGBA",(1024,1024),(0,0,0,0)); d=_SmoothDraw(im)
    skin=SKIN[settings["skin"]]; hair=HAIR_COLORS[settings["hair_color"]]
    style=settings["hair"]
    if style=="Long": d.rounded_rectangle((61,40,195,206),radius=54,fill=hair)
    if style=="Bob": d.rounded_rectangle((60,43,196,163),radius=38,fill=hair)
    if style=="Ponytail": d.ellipse((171,71,223,193),fill=hair)
    if style=="Bun": d.ellipse((101,12,155,66),fill=hair)
    d.ellipse((40,173,216,330),fill=CLOTHES[settings["clothing"]])
    d.arc((51,181,205,293),192,348,fill=_tint(CLOTHES[settings["clothing"]],"#FFFFFF",.25),width=2)
    d.rectangle((109,156,147,195),fill=skin)
    d.ellipse((109,169,147,191),fill=_tint(skin,"#50382F",.15))
    d.arc((104,176,152,202),0,180,fill=_tint(CLOTHES[settings["clothing"]],"#FFFFFF",.5),width=3)
    for x in (65,177):
        d.ellipse((x,104,x+14,135),fill=skin)
        d.arc((x+4,111,x+11,129),90,270,fill=_tint(skin,"#50382F",.18),width=1)
    d.ellipse((69,47,187,181),fill=skin)
    if style in ("Short","Long","Bob","Ponytail","Bun"):
        d.pieslice((64,37,191,120),180,360,fill=hair)
        d.polygon([(66,82),(124,49),(181,80),(160,56),(110,45)],fill=hair)
    if settings["hair"]=="Curly":
        for x,y in [(78,61),(99,47),(125,44),(150,47),(174,61)]:
            d.ellipse((x-20,y-20,x+20,y+20),fill=hair)
    if style=="Mohawk":
        d.polygon([(110,71),(113,19),(127,7),(143,21),(148,71)],fill=hair)
    if style=="Spiky":
        d.polygon([(64,83),(69,38),(88,50),(97,19),(116,42),(132,13),(147,42),(167,24),(175,57),(194,43),(188,87)],fill=hair)
    if style=="Side swept":
        d.pieslice((64,34,191,118),180,360,fill=hair)
        d.polygon([(69,70),(173,47),(168,84),(114,105)],fill=hair)
    # Fine hair highlights follow the silhouette without changing the saved style.
    highlight=_tint(hair,"#FFFFFF",.18)
    if style in ("Short","Long","Bob","Ponytail","Bun","Side swept"):
        for offset in (0,7,14):
            d.arc((78+offset,46+offset/3,177-offset,95+offset/3),195,290,fill=highlight,width=1)
    if style=="Curly":
        for x,y in [(78,61),(99,47),(125,44),(150,47),(174,61)]:
            d.arc((x-12,y-13,x+10,y+9),195,300,fill=highlight,width=1)
    if style in ("Long","Bob"):
        for x in (64,68,188,192):d.line((x,108,x,147 if style=="Bob" else 176),fill=highlight,width=1)
    d.arc((90,98,109,105),190,345,fill=hair,width=2)
    d.arc((147,98,166,105),195,350,fill=hair,width=2)
    d.arc((122,117,133,135),320,100,fill=_tint(skin,"#50382F",.28),width=2)
    d.ellipse((88,128,104,134),fill=_tint(skin,"#D87879",.28))
    d.ellipse((152,128,168,134),fill=_tint(skin,"#D87879",.28))
    d.ellipse((95,108,104,119),fill="#242437"); d.ellipse((152,108,161,119),fill="#242437")
    d.ellipse((97,109,100,112),fill="#FFFFFF");d.ellipse((154,109,157,112),fill="#FFFFFF")
    d.arc((108,128,150,152),0,180,fill="#6A3E3C",width=3)
    if settings["accessory"]=="Glasses":
        for x in [86,139]: d.rounded_rectangle((x,101,x+32,129),radius=9,outline="#35364D",width=4)
        d.line((118,111,139,111),fill="#35364D",width=3)
    if settings["accessory"]=="Hat":
        d.rounded_rectangle((76,26,180,70),radius=14,fill="#343C76")
        d.rounded_rectangle((58,61,200,78),radius=7,fill="#343C76")
    accessory=settings["accessory"]
    if accessory=="Sunglasses":
        for x in (83,139): d.rounded_rectangle((x,101,x+36,128),radius=7,fill="#242437")
        d.line((119,110,139,110),fill="#242437",width=4)
    elif accessory=="Headphones":
        d.arc((54,41,202,175),180,360,fill="#424C91",width=9)
        for x in (54,184):d.rounded_rectangle((x,100,x+18,147),radius=7,fill="#424C91")
    elif accessory=="Earrings":
        for x in (65,181):d.ellipse((x,139,x+13,158),outline="#D9A632",width=4)
    elif accessory=="Headband":
        d.arc((66,48,190,155),188,352,fill="#E56C91",width=12)
    elif accessory=="Bow":
        d.polygon([(163,53),(141,35),(143,69)],fill="#DF679C")
        d.polygon([(163,53),(184,33),(187,69)],fill="#DF679C")
        d.ellipse((157,46,170,59),fill="#B84980")
    elif accessory=="Crown":
        d.polygon([(83,62),(78,26),(106,43),(127,15),(150,42),(177,26),(173,62)],fill="#EDC85B")
        for x in (103,127,151):d.ellipse((x-3,49,x+3,55),fill="#8E6AD5")
    elif accessory=="Scarf":
        d.rounded_rectangle((95,169,162,191),radius=8,fill="#E47964")
        d.polygon([(139,183),(163,184),(168,223),(146,216)],fill="#E47964")
    elif accessory=="Monocle":
        d.ellipse((142,99,173,131),outline="#AD8B38",width=3)
        d.arc((159,118,191,181),270,100,fill="#AD8B38",width=2)
    im=im.resize((512,512),Image.Resampling.LANCZOS)
    out=io.BytesIO();im.save(out,format="PNG");return out.getvalue()

def crop_photo(data,x=.5,y=.5,zoom=1):
    if len(data)>5*1024*1024: raise ValueError("Choose a photo smaller than 5 MB.")
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.format not in ("JPEG","PNG") or source.width*source.height>20_000_000:
                raise ValueError("Choose a JPEG or PNG under 20 megapixels.")
            source.load()
            im=ImageOps.exif_transpose(source).convert("RGB")
        if not (0<=x<=1 and 0<=y<=1 and 1<=zoom<=3): raise ValueError("Invalid crop.")
        side=int(min(im.size)/zoom)
        left=int((im.width-side)*x); top=int((im.height-side)*y)
        crop=im.crop((left,top,left+side,top+side)).resize((256,256),Image.Resampling.LANCZOS)
        clean=Image.new("RGB",crop.size);clean.paste(crop)
        out=io.BytesIO();clean.save(out,format="PNG");return out.getvalue()
    except (OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ValueError("That file is not a supported photo. Choose a JPEG or PNG.") from exc


def normalize_friend_code(value):
    value=value.strip().removeprefix('#').upper()
    if not re.fullmatch(r'[A-HJ-NP-Z2-9]{8}',value):
        raise ValueError('Enter the eight letters and numbers shown in your friend’s code.')
    return value


def invitation_token(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-f0-9]{48}',value):
        raise ValueError('This invitation is invalid or expired.')
    return value


def invitation_url(base,token):
    from urllib.parse import urlsplit, urlencode
    parsed=urlsplit(base)
    if parsed.scheme!='https' or not parsed.hostname or parsed.hostname in ('localhost','127.0.0.1','::1') or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Invitation sharing needs the public HTTPS app address.')
    return base.rstrip('/')+'/?'+urlencode({'invite':invitation_token(token)})

# Deck content is separate from future duel progress.
from copy import deepcopy
from uuid import uuid4, UUID
import hashlib
import json

def new_card():
    return {'id':str(uuid4()),'question':'','answers':[{'id':str(uuid4()),'text':''} for _ in range(4)],'correct_answer_id':None}

def new_deck(course='',language=''):
    return {'id':str(uuid4()),'course':course,'language':language,'name':'','cards':[new_card()]}

def _deck_id(value):
    try:
        if not isinstance(value,str) or str(UUID(value))!=value:raise ValueError()
    except (ValueError,TypeError,AttributeError):raise ValueError('Invalid card or answer identity.')
    return value

def _deck_text(value,label):
    if not isinstance(value,str) or not value.strip():raise ValueError(f'Enter {label}.')
    return value.strip()

def validate_card(card):
    if not isinstance(card,dict):raise ValueError('Complete this card.')
    answers=card.get('answers')
    if not isinstance(answers,list) or len(answers)!=4:raise ValueError('Each card needs exactly four answers.')
    clean=[]
    for i,a in enumerate(answers):
        if not isinstance(a,dict):raise ValueError('Complete all four answers.')
        clean.append({'id':_deck_id(a.get('id')),'text':_deck_text(a.get('text'),f'Answer {i+1}')})
    ids=[a['id'] for a in clean]
    if len(set(ids))!=4:raise ValueError('Answer identities must be unique.')
    correct=card.get('correct_answer_id')
    if not isinstance(correct,str) or correct not in ids:raise ValueError('Select exactly one correct answer.')
    return {'id':_deck_id(card.get('id')),'question':_deck_text(card.get('question'),'a question'),'answers':clean,'correct_answer_id':correct}

def validate_deck(draft):
    if not isinstance(draft,dict):raise ValueError('Create a deck first.')
    cards=draft.get('cards')
    if not isinstance(cards,list) or len(cards)!=15:raise ValueError('A deck must contain exactly 15 complete cards.')
    clean=[]
    for i,c in enumerate(cards):
        try:clean.append(validate_card(c))
        except ValueError as exc:raise ValueError(f'Card {i+1}: {exc}') from exc
    ids=[c['id'] for c in clean]+[a['id'] for c in clean for a in c['answers']]
    if len(set(ids))!=75:raise ValueError('Card and answer identities must be unique.')
    language=draft.get('language')
    if language not in LANGUAGES:raise ValueError('Select a deck language from your profile.')
    return {'language':language,'id':_deck_id(draft.get('id')),'course':_deck_text(draft.get('course'),'a course'),'name':_deck_text(draft.get('name'),'a deck name'),'cards':clean}

def deck_fingerprint(draft):
    return hashlib.sha256(json.dumps(validate_deck(draft),sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def add_card(draft,index=None):
    if len(draft['cards'])>=15:raise ValueError('A deck has at most 15 cards.')
    if draft['cards']:validate_card(draft['cards'][-1 if index is None else index])
    result=deepcopy(draft);result['cards'].append(new_card());return result

def delete_card(draft,index):
    if type(index) is not int or not 0<=index<len(draft['cards']):raise ValueError('Choose a card to delete.')
    result=deepcopy(draft);result['cards'].pop(index)
    if not result['cards']:result['cards']=[new_card()]
    return result
