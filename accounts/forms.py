from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, BaseUserCreationForm, PasswordChangeForm

User = get_user_model()

INPUT = (
    "w-full rounded-[10px] bg-white px-4 py-3 text-sm ring-1 ring-line placeholder:text-muted "
    "focus:outline-none focus:ring-2 focus:ring-brand aria-[invalid=true]:ring-[#b42318]"
)
CHECKBOX = "mt-0.5 h-4 w-4 shrink-0 accent-brand"


def email_taken(email, exclude_pk=None):
    """Login memakai username = email huruf kecil; akun lama (mis. admin) bisa punya email saja."""
    qs = User.objects.filter(username__iexact=email) | User.objects.filter(email__iexact=email)
    return qs.exclude(pk=exclude_pk).exists()


class Styled:
    """Kelas Tailwind dan aria-invalid untuk semua field, supaya template tidak mengulang."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css = CHECKBOX if isinstance(widget, forms.CheckboxInput) else INPUT
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                self.fields[name].widget.attrs["aria-invalid"] = "true"


class RegisterForm(Styled, BaseUserCreationForm):
    display_name = forms.CharField(label="Nama tampilan", max_length=150)
    email = forms.EmailField(label="Email", max_length=150)
    terms = forms.BooleanField(
        label="Saya setuju dengan Ketentuan Layanan dan memahami PilihYuk bukan alat diagnosis medis.",
        error_messages={"required": "Centang persetujuan untuk melanjutkan."},
    )

    class Meta:
        model = User
        fields = ("email",)  # username dan first_name diisi di clean(); is_staff tidak pernah ikut

    field_order = ["display_name", "email", "password1", "password2", "terms"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["display_name"].widget.attrs["autocomplete"] = "name"
        self.fields["email"].widget.attrs["autocomplete"] = "email"
        self.fields["password1"].label = "Password"
        self.fields["password1"].help_text = "Minimal 8 karakter. Gunakan kombinasi huruf dan angka."
        self.fields["password2"].label = "Konfirmasi password"
        self.fields["password2"].help_text = ""

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if email_taken(email):
            raise forms.ValidationError("Email ini sudah terdaftar. Coba masuk.")
        return email

    def clean(self):
        cleaned = super().clean()
        # Diisi sebelum validasi password agar UserAttributeSimilarityValidator punya bahan.
        self.instance.username = cleaned.get("email", "")
        self.instance.first_name = cleaned.get("display_name", "")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        user.first_name = self.cleaned_data["display_name"]
        if commit:
            user.save()
        return user


class LoginForm(Styled, AuthenticationForm):
    username = forms.CharField(label="Email", max_length=150)
    remember = forms.BooleanField(label="Ingat saya selama 30 hari", required=False)
    error_messages = {
        **AuthenticationForm.error_messages,
        # Satu pesan untuk email salah maupun password salah (tanpa membocorkan akun mana yang ada).
        "invalid_login": "Email atau password salah.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(autocomplete="username", inputmode="email", autofocus=True)
        self.fields["password"].label = "Password"

    def clean_username(self):
        value = self.cleaned_data["username"].strip()
        # Email disimpan huruf kecil; username admin tanpa "@" dibiarkan apa adanya.
        return value.lower() if "@" in value else value


class ProfileForm(Styled, forms.Form):
    display_name = forms.CharField(label="Nama tampilan", max_length=150)
    email = forms.EmailField(label="Email", max_length=150)
    current_password = forms.CharField(
        label="Password saat ini",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        help_text="Wajib diisi hanya bila kamu mengganti email.",
    )

    def __init__(self, *args, user, **kwargs):
        kwargs.setdefault("initial", {"display_name": user.first_name, "email": user.email})
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email")
        # Sesi yang dicuri tidak boleh cukup untuk mengganti email (dan username login).
        if email and email != self.user.email.lower() and not self.user.check_password(cleaned.get("current_password", "")):
            self.add_error("current_password", "Masukkan password saat ini untuk mengganti email.")
        return cleaned

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if email_taken(email, exclude_pk=self.user.pk):
            raise forms.ValidationError("Email ini sudah dipakai akun lain.")
        return email

    def save(self):
        self.user.first_name = self.cleaned_data["display_name"]
        self.user.email = self.user.username = self.cleaned_data["email"]
        self.user.save(update_fields=["first_name", "email", "username"])
        return self.user


class StyledPasswordChangeForm(Styled, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Password lama"
        self.fields["new_password1"].label = "Password baru"
        self.fields["new_password1"].help_text = "Minimal 8 karakter. Gunakan kombinasi huruf dan angka."
        self.fields["new_password2"].label = "Konfirmasi password baru"
        self.fields["new_password2"].help_text = ""
