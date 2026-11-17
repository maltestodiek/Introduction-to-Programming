"""Supabase repositories. All requests use the signed-in user's JWT."""
from uuid import uuid4
from logic import validate_profile

class ProfileRepository:
    def __init__(self,client,user_id):
        self.client=client
        self.user_id=user_id

    def load(self):
        a=self.client.table("profiles").select("*").eq("id",self.user_id).execute().data
        b=self.client.table("profile_private").select("*").eq("user_id",self.user_id).execute().data
        if not a or not b: return None
        return {**a[0],**b[0]}

    def image(self,path):
        if not path:return None
        return self.client.storage.from_("profile-images").download(path)

    def save(self,data,mode,image,old_path):
        data=validate_profile(**data)
        if mode not in ("Avatar","Photo"): raise ValueError("Choose an image mode.")
        path=old_path
        uploaded=False
        try:
            if image is not None:
                path=f"{self.user_id}/{uuid4().hex}.png"
                self.client.storage.from_("profile-images").upload(
                    path,image,{"content-type":"image/png","upsert":"false"})
                uploaded=True
            self.client.rpc("save_profile_v3",{
                "p_username":data["username"],"p_university":data["university"],
                "p_languages":data["languages"],"p_courses":data["courses"],
                "p_graduation_year":data["graduation_year"],
                "p_degree":data["degree"],"p_area":data["area"],
                "p_avatar":data["avatar"],"p_image_mode":mode,"p_image_path":path,
            }).execute()
        except Exception as exc:
            # A timed-out response may follow a successful transaction. Retain the
            # uploaded object rather than deleting an image that may now be active.
            if getattr(exc,"code","")=="23505":
                raise ValueError("That username is taken. Choose another.") from exc
            raise ValueError("Your save could not be confirmed. Reload your profile before retrying; check that the username is available.") from exc
        if uploaded and old_path and old_path!=path:
            try:self.client.storage.from_("profile-images").remove([old_path])
            except Exception:pass  # Old unreferenced image remains owner-only.


class FriendsRepository:
    """All identities and relationship permissions are checked inside Supabase."""
    def __init__(self,client):self.client=client

    def action(self,action,value=''):
        try:
            result=self.client.rpc('friends_action',{'p_action':action,'p_value':value}).execute().data
        except Exception as exc:
            raise ValueError('Could not confirm this action. Refresh your friends list before retrying.') from exc
        if not isinstance(result,dict):raise ValueError('Could not load your friends. Refresh and try again.')
        if result.get('error'):raise ValueError(result['error'])
        return result

    def lookup(self,code):
        from logic import normalize_friend_code
        return self.action('lookup',normalize_friend_code(code))

class DeckRepository:
    """Reviewed snapshots and atomic publication under the signed-in identity."""
    def __init__(self,client):self.client=client

    def review(self,draft):
        from logic import validate_deck,deck_fingerprint
        clean=validate_deck(draft)
        try:r=self.client.rpc('review_deck',{'p_draft':clean}).execute().data
        except Exception as exc:raise ValueError('Could not prepare the review. Check your selected course and try again.') from exc
        return {'id':r['id'],'fingerprint':deck_fingerprint(clean)}

    def publish(self,draft,review):
        from logic import validate_deck,deck_fingerprint
        clean=validate_deck(draft)
        if not review or review.get('fingerprint')!=deck_fingerprint(clean):raise ValueError('This deck changed. Open a new review before publishing.')
        try:return self.client.rpc('publish_deck',{'p_review_id':review['id'],'p_draft':clean}).execute().data
        except Exception as exc:raise ValueError('Publication could not be confirmed. Retry Create Deck; the same draft will not be published twice.') from exc

    def list(self,course):
        try:return self.client.table('decks').select('id,name,course,language,creator_id,created_at,profiles(username)').ilike('course',course.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')).order('created_at',desc=True).execute().data
        except Exception as exc:raise ValueError('Could not load decks. Please try again.') from exc

    def get(self,deck_id):
        try:rows=self.client.table('decks').select('*,profiles(username)').eq('id',deck_id).execute().data
        except Exception as exc:raise ValueError('Could not load this deck. Please try again.') from exc
        if not rows:raise ValueError('This deck is unavailable at your university.')
        return rows[0]


class AnkiImportRepository:
    """Private source imports and reviewable AI drafts under the current JWT."""
    def __init__(self,client): self.client=client

    def save(self, *, name, course, language, cards):
        try:
            return self.client.rpc('import_basic_anki',{'p_name':name,'p_course':course,'p_language':language,'p_cards':cards}).execute().data
        except Exception as exc:
            raise ValueError('The Anki import could not be saved. Your file and imported cards are unchanged; try again.') from exc

    def save_slides(self, *, name, course, language, cards):
        try:return self.client.rpc('import_pdf_slides',{'p_name':name,'p_course':course,'p_language':language,'p_cards':cards}).execute().data
        except Exception as exc:raise ValueError('The PDF import could not be saved. Your extracted text is unchanged; try again.') from exc

    def imports(self):
        try:
            imports=self.client.table('anki_imports').select('id,name,course,language,source_type,created_at').order('created_at',desc=True).execute().data
            cards=self.client.table('anki_source_cards').select('id,import_id,position,front,back').order('position').execute().data
            drafts=self.client.table('ai_question_drafts').select('id,import_id,source_card_id,question,options,correct_option_index,explanation,status,created_at').order('created_at').execute().data
        except Exception as exc:
            raise ValueError('Could not load your Anki imports. Refresh and try again.') from exc
        for imported in imports:
            imported['cards']=[card for card in cards if card['import_id']==imported['id']]
            imported['drafts']=[draft for draft in drafts if draft['import_id']==imported['id']]
        return imports

    def generate(self, import_id, card_ids):
        if not isinstance(card_ids,list) or not 1<=len(card_ids)<=100:
            raise ValueError('Select between 1 and 100 source cards.')
        try:
            result=self.client.functions.invoke('generate-questions',invoke_options={'body':{'importId':import_id,'cardIds':card_ids}})
            data=getattr(result,'data',result)
        except Exception as exc:
            detail='Question generation could not be completed. Your source cards are unchanged; try again.'
            for response in (getattr(exc,'context',None),getattr(exc,'response',None)):
                try:
                    payload=response if isinstance(response,dict) else response.json()
                    if isinstance(payload,dict) and isinstance(payload.get('error'),str):
                        detail=payload['error'];break
                except Exception:pass
            if detail.startswith('Question generation could not'):
                message=str(exc).strip()
                if message and message not in {'Error invoking remote function','FunctionsHttpError'}:
                    detail=f'Question generation failed: {message}'
            raise ValueError(detail) from exc
        if not isinstance(data,dict) or data.get('status')!='draft':
            raise ValueError('Question generation returned an unexpected result. No source cards were changed.')
        return data

    def update_draft(self, draft_id, question, options, correct_option_index):
        try:
            return self.client.rpc('update_ai_question_draft',{'p_draft_id':draft_id,'p_question':question,'p_options':options,'p_correct_option_index':correct_option_index}).execute().data
        except Exception as exc:
            raise ValueError('This draft could not be saved. Check all four answers and try again.') from exc

    def discard_draft(self, draft_id):
        try:self.client.rpc('discard_ai_question_draft',{'p_draft_id':draft_id}).execute()
        except Exception as exc:raise ValueError('This draft could not be discarded. Refresh and try again.') from exc

    def publish_drafts(self, draft_ids):
        try:self.client.rpc('publish_ai_question_drafts',{'p_draft_ids':draft_ids}).execute()
        except Exception as exc:raise ValueError('Your deck was saved, but its source drafts could not be marked published. Refresh before retrying.') from exc


class PlayRepository:
    """Server-authoritative matchmaking and rounds under the current user's JWT."""
    def __init__(self,client):self.client=client

    def action(self,action,data=None):
        try:
            result=self.client.rpc('play_action',{'p_action':action,'p_data':data or {}}).execute().data
        except Exception as exc:
            raise ValueError('Could not confirm this Play action. Refresh Play before retrying.') from exc
        if not isinstance(result,dict):raise ValueError('Could not load Play. Please try again.')
        if result.get('error'):raise ValueError(result['error'])
        return result


class BattleRepository:
    """Server-authoritative 15-question Battle Mode operations."""
    def __init__(self,client):self.client=client

    def action(self,action,data=None):
        try:result=self.client.rpc('battle_action',{'p_action':action,'p_data':data or {}}).execute().data
        except Exception as exc:raise ValueError(battle_error_message(exc)) from exc
        if not isinstance(result,dict):raise ValueError('Battle Mode returned an unexpected result.')
        if result.get('error'):raise ValueError(result['error'])
        return result


def battle_error_message(error):
    """Expose approved Battle eligibility feedback without leaking database details."""
    message=str(error)
    known={
        'No eligible Battle Deck is available for this course and language':'Not able to start this Battle: no public 15-question Battle Deck matches the selected course and language yet.',
        'There is already a pending Battle invitation between you':'Outstanding invitation: you already have a pending Battle invitation with this friend.',
        'Your friend needs this course, language and university in their profile':'Not able to invite this friend: they have not selected this course, language, or university in their profile.',
        'Choose an accepted friend':'Not able to invite this user: they are not an accepted friend.',
        'Choose an eligible Top Deck':'Not able to start this Battle: choose a currently eligible Top Deck.',
        'Choose one of your courses and languages':'Not able to start this Battle: choose a course and language from your profile.',
        'Complete your profile first':'Not able to use Battle Mode: complete your university, course, and language profile first.',
        'Battle invitation unavailable':'This Battle invitation is no longer available.',
        'Only the invited friend can respond':'Only the invited friend can accept or decline this invitation.',
        'Only the sender can cancel':'Only the sender can cancel this invitation.',
    }
    for item,feedback in known.items():
        if item in message:return feedback
    return 'Battle Mode could not be reached. Refresh and retry after its database migration is applied.'


class LeaderboardRepository:
    """Read-only Game XP rankings through the authenticated database function."""
    def __init__(self,client):self.client=client

    def load(self):
        try:result=self.client.rpc('leaderboard',{}).execute().data
        except Exception as exc:raise ValueError('The leaderboard could not be reached. Refresh and retry.') from exc
        if not isinstance(result,dict):raise ValueError('The leaderboard is temporarily unavailable.')
        if result.get('error'):raise ValueError(result['error'])
        return result


class StudyRepository:
    """Authenticated, transactional Study operations. Never accepts a user ID."""
    def __init__(self,client):self.client=client

    def action(self,action,data=None):
        try:result=self.client.rpc('study_action',{'p_action':action,'p_data':data or {}}).execute().data
        except Exception as exc:raise ValueError('Could not confirm this Study action. Refresh and retry. If Study is not set up yet, apply its database migration.') from exc
        if not isinstance(result,dict):raise ValueError('Could not load Study Mode.')
        if result.get('error'):raise ValueError(result['error'])
        return result

    def publication(self,action,data=None):
        try:result=self.client.rpc('study_public_action',{'p_action':action,'p_data':data or {}}).execute().data
        except Exception as exc:raise ValueError('Could not update Study deck publishing. Refresh and retry.') from exc
        if not isinstance(result,dict):raise ValueError('Could not load published Study decks.')
        if result.get('error'):raise ValueError(result['error'])
        return result


class ChatRepository:
    """Participant-only chat through the existing authenticated Supabase client."""
    def __init__(self,client):self.client=client

    def action(self,action,data=None):
        try:result=self.client.rpc('chat_action',{'p_action':action,'p_data':data or {}}).execute().data
        except Exception as exc:raise ValueError('Chat could not be reached. Your message is kept so you can retry.') from exc
        if not isinstance(result,dict):raise ValueError('Chat is temporarily unavailable.')
        if result.get('error'):raise ValueError(result['error'])
        return result


class StudyPlanRepository:
    """Owner-only study plans through an authenticated Supabase RPC. Never accepts a user ID."""
    def __init__(self,client):self.client=client

    def action(self,action,data=None):
        try:result=self.client.rpc('study_plan_action',{'p_action':action,'p_data':data or {}}).execute().data
        except Exception as exc:raise ValueError('Study plans could not be reached. Nothing was changed; refresh and retry. If study plans are not set up yet, apply their database migration.') from exc
        if not isinstance(result,dict):raise ValueError('Study plans are temporarily unavailable.')
        if result.get('error'):raise ValueError(result['error'])
        return result
