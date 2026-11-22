"""Supabase repositories. All requests use the signed-in user's JWT."""
import json
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

    def save(self,data,mode,image,old_path, *, previous=None):
        from course_catalog import other_university_courses
        previous = previous or {}
        university = " ".join(data["university"].split())
        supports_history = "course_history" in previous
        if previous and university != previous["university"] and not supports_history:
            raise ValueError("Switching universities requires the course history database update. Your profile is unchanged.")
        data=validate_profile(**data, has_other_courses=bool(other_university_courses(previous, university)))
        if mode not in ("Avatar","Photo"): raise ValueError("Choose an image mode.")
        path=old_path
        uploaded=False
        try:
            if image is not None:
                path=f"{self.user_id}/{uuid4().hex}.png"
                self.client.storage.from_("profile-images").upload(
                    path,image,{"content-type":"image/png","upsert":"false"})
                uploaded=True
            params = {
                "p_username":data["username"],"p_university":data["university"],
                "p_languages":data["languages"],"p_courses":data["courses"],
                "p_graduation_year":data["graduation_year"],
                "p_degree":data["degree"],"p_area":data["area"],
                "p_avatar":data["avatar"],"p_image_mode":mode,"p_image_path":path,
            }
            if supports_history:
                params["p_expected_university"] = previous["university"]
            self.client.rpc("save_profile_v4" if supports_history else "save_profile_v3", params).execute()
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

    def university_profiles(self):
        try:result=self.client.rpc('university_friend_profiles',{}).execute().data
        except Exception as exc:raise ValueError('Could not load students from your university. Refresh and try again.') from exc
        if not isinstance(result,dict):raise ValueError('Could not load students from your university. Refresh and try again.')
        if result.get('error'):raise ValueError(result['error'])
        if not isinstance(result.get('profiles'),list):raise ValueError('Could not load students from your university. Refresh and try again.')
        return result

    def request_university_friend(self,user_id):
        try:result=self.client.rpc('request_university_friend',{'p_user_id':user_id}).execute().data
        except Exception as exc:raise ValueError('Could not send this friend request. Refresh and try again.') from exc
        if not isinstance(result,dict):raise ValueError('Could not send this friend request. Refresh and try again.')
        if result.get('error'):raise ValueError(result['error'])
        return result

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
        # supabase-py returns the raw body (bytes) unless responseType is "json".
        if isinstance(data,(bytes,bytearray,str)):
            try:data=json.loads(data)
            except ValueError:data=None
        if not isinstance(data,dict) or data.get('status')!='draft':
            raise ValueError('Question generation returned an unexpected result. No source cards were changed.')
        return data

    def read_image_text(self, images):
        """Read the text on the images of one Anki card through the extract-image-text Edge Function.

        Returns {image id: text}. Nothing is stored; the student reviews the text before importing.
        """
        import base64
        body={'images':[{'id':image['id'],'mime':image['mime'],'data':base64.b64encode(image['data']).decode()} for image in images]}
        unreadable='The text on this image could not be read. Try again or type it yourself.'
        try:
            result=self.client.functions.invoke('extract-image-text',invoke_options={'body':body})
            data=getattr(result,'data',result)
        except Exception as exc:
            detail=unreadable
            for response in (getattr(exc,'context',None),getattr(exc,'response',None)):
                try:
                    payload=response if isinstance(response,dict) else response.json()
                    if isinstance(payload,dict) and isinstance(payload.get('error'),str):
                        detail=payload['error'];break
                except Exception:pass
            raise ValueError(detail) from exc
        if isinstance(data,(bytes,bytearray,str)):
            try:data=json.loads(data)
            except ValueError:data=None
        texts=data.get('texts') if isinstance(data,dict) else None
        if not isinstance(texts,list) or not all(isinstance(item,dict) and isinstance(item.get('id'),str) and isinstance(item.get('text'),str) for item in texts):
            raise ValueError(unreadable)
        return {item['id']:item['text'] for item in texts}

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


def play_unread_updates(client, seen=()):
    try:
        data = client.rpc('play_unread_updates', {'p_seen':sorted(seen)}).execute().data
    except Exception:
        return None
    return set(data) if isinstance(data, list) and all(isinstance(k,str) for k in data) else None


class BattleRepository:
    """Server-authoritative 15-question Battle Mode operations."""
    def __init__(self,client):self.client=client

    def action(self,action,data=None):
        try:result=self.client.rpc('battle_action',{'p_action':action,'p_data':data or {}}).execute().data
        except Exception as exc:raise ValueError(battle_error_message(exc)) from exc
        if not isinstance(result,dict):raise ValueError('Battle Mode returned an unexpected result.')
        if result.get('error'):raise ValueError(result['error'])
        if action=='list' and not result.get('includes_unmatched'):result['sessions']=self.sessions()
        return result

    def availability(self,course,language):
        """Return whether the selected criteria have an eligible Battle Deck."""
        try:result=self.client.rpc('battle_deck_availability',{'p_course':course,'p_language':language}).execute().data
        except Exception as exc:raise ValueError(battle_error_message(exc)) from exc
        if not isinstance(result,dict) or not isinstance(result.get('available'),bool):
            raise ValueError('Battle Deck availability could not be loaded. Refresh and retry.')
        return result

    def catalog(self):
        """Public Battle Decks of the user's university and courses, metadata only."""
        message='Battle decks could not be loaded. Refresh and retry.'
        try:result=self.client.rpc('battle_deck_catalog',{}).execute().data
        except Exception as exc:raise ValueError(message) from exc
        decks=result.get('decks') if isinstance(result,dict) else None
        if not isinstance(decks,list):raise ValueError(message)
        return decks

    def cancel_search(self):
        """Cancel only the signed-in user's pending random Battle search."""
        try:result=self.client.rpc('cancel_battle_search',{}).execute().data
        except Exception as exc:raise ValueError('This Battle search could not be cancelled. Refresh and retry.') from exc
        if not isinstance(result,dict):raise ValueError('This Battle search could not be cancelled. Refresh and retry.')
        return result

    def sessions(self):
        """Return Battle rows enriched with the opponent's visible username."""
        try:result=self.client.rpc('battle_sessions_list',{}).execute().data
        except Exception as exc:raise ValueError('Battle sessions could not be loaded. Refresh and retry.') from exc
        if not isinstance(result,list):raise ValueError('Battle sessions returned an unexpected result.')
        return result

    def report_question(self,session_id,card_index,reason,note=''):
        """Save one participant-only report for a completed Battle question."""
        try:
            result=self.client.rpc('report_battle_question',{
                'p_session':session_id,'p_card_index':card_index,
                'p_reason':reason,'p_note':note,
            }).execute().data
        except Exception as exc:raise ValueError(question_report_error_message(exc)) from exc
        if not isinstance(result,dict):raise ValueError('This question report could not be saved. Refresh and retry.')
        return result

    def progress(self,session_id):
        try:result=self.client.rpc('battle_round_progress',{'p_session':session_id}).execute().data
        except Exception as exc:raise ValueError('Battle progress could not be loaded. Refresh and retry.') from exc
        if not isinstance(result,dict):raise ValueError('Battle progress returned an unexpected result.')
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
        'You already have an active random search':'Finish or cancel your existing random search in Active battles before choosing different settings.',
        'Battle unavailable':'This Battle is unavailable. Return to Active battles to see your current games.',
        'Battle invitation unavailable':'This Battle invitation is no longer available.',
        'Only the invited friend can respond':'Only the invited friend can accept or decline this invitation.',
        'Only the sender can cancel':'Only the sender can cancel this invitation.',
    }
    for item,feedback in known.items():
        if item in message:return feedback
    return 'Battle Mode could not be reached. Refresh and retry after its database migration is applied.'


def question_report_error_message(error):
    """Give a deployable report feature a useful setup message without exposing SQL details."""
    if 'report_battle_question' in str(error):
        return 'Question reports are not set up yet. Apply the Battle question reports database migration, then refresh.'
    return 'This question report could not be saved. Refresh and retry.'


class LeaderboardRepository:
    """Read-only Battle XP rankings through the authenticated database function."""
    def __init__(self,client):self.client=client

    def load(self):
        try:result=self.client.rpc('leaderboard_30_days',{}).execute().data
        except Exception as exc:raise ValueError('The leaderboard could not be reached. Refresh and retry.') from exc
        if not isinstance(result,dict):raise ValueError('The leaderboard is temporarily unavailable.')
        if result.get('error'):raise ValueError(result['error'])
        return result

    def university_top(self, viewer):
        """Read at most ten public ranking rows for the signed-in viewer's campus."""
        university = viewer.get('university')
        if not university or not university.strip():
            return []
        try:
            rows = (self.client.table('profiles').select('username,image_path,game_xp')
                    .eq('university', university).order('game_xp', desc=True)
                    .order('username').limit(10).execute().data)
        except Exception as exc:
            raise ValueError('Your university ranking could not be loaded. Refresh to try again.') from exc
        if not isinstance(rows,list):
            raise ValueError('Your university ranking is temporarily unavailable.')
        ranking = []
        previous_xp = None
        for position, row in enumerate(rows, start=1):
            xp = row['game_xp']
            if position == 1 or xp != previous_xp:
                rank = position
            ranking.append({'rank':rank, 'username':row['username'], 'xp':xp,
                            'university':university, 'image_path':row['image_path'],
                            'me':row['username'] == viewer['username']})
            previous_xp = xp
        return ranking


class StudyRepository:
    """Authenticated, transactional Study operations. Never accepts a user ID."""
    def __init__(self,client):self.client=client

    def action(self,action,data=None):
        try:
            if action == 'list' and data and data.get('session_overview'):
                result = self.client.rpc('study_session_dashboard', {}).execute().data
            else:
                result = self.client.rpc('study_action', {'p_action':action, 'p_data':data or {}}).execute().data
        except Exception as exc:raise ValueError('Could not confirm this Study action. Refresh and retry. If Study is not set up yet, apply its database migration.') from exc
        if not isinstance(result,dict):raise ValueError('Could not load Study Mode.')
        if result.get('error'):raise ValueError(result['error'])
        return result

    def studio(self):
        """The signed-in student's own Study and Battle decks with creation, edit and publication times."""
        message='Your decks could not be loaded. Refresh and retry.'
        try:result=self.client.rpc('deck_studio',{}).execute().data
        except Exception as exc:raise ValueError(message) from exc
        decks=result.get('decks') if isinstance(result,dict) else None
        if not isinstance(decks,list):raise ValueError(message)
        return decks

    def progress(self,session_id):
        try:result=self.client.rpc('study_session_progress',{'p_session':session_id}).execute().data
        except Exception as exc:raise ValueError('Study progress could not be loaded. Refresh and retry.') from exc
        if not isinstance(result,dict):raise ValueError('Study progress returned an unexpected result.')
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
