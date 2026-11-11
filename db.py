"""Supabase profile repository. All requests use the signed-in user's JWT."""
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
            self.client.rpc("save_profile_v2",{
                "p_username":data["username"],"p_university":data["university"],
                "p_languages":data["languages"],"p_courses":data["courses"],
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
