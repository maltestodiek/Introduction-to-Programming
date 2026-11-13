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
    """Saves normalized source cards through an authenticated Supabase RPC only."""
    def __init__(self,client): self.client=client

    def save(self, *, name, course, language, cards):
        try:
            return self.client.rpc('import_basic_anki',{'p_name':name,'p_course':course,'p_language':language,'p_cards':cards}).execute().data
        except Exception as exc:
            raise ValueError('The Anki import could not be saved. Your file and imported cards are unchanged; try again.') from exc


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


class StudyRepository:
    """Authenticated, transactional Study operations. Never accepts a user ID."""
    def __init__(self,client):self.client=client

    def action(self,action,data=None):
        try:result=self.client.rpc('study_action',{'p_action':action,'p_data':data or {}}).execute().data
        except Exception as exc:raise ValueError('Could not confirm this Study action. Refresh and retry. If Study is not set up yet, apply its database migration.') from exc
        if not isinstance(result,dict):raise ValueError('Could not load Study Mode.')
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
