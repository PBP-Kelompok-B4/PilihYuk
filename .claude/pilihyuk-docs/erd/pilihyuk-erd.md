# ERD PilihYuk

Sumber: model data yang disepakati kelompok. Ada dua versi diagram yang isinya sama:

- `pilihyuk.drawio`: acuan utama. Tabel dan garis memakai elemen bawaan sidebar Entity Relation draw.io (Table dan garis relasi), jadi baris bisa disunting, ditambah, dan dihapus langsung, dan tiap garis menempel ke baris kuncinya. Buka di https://app.diagrams.net lewat File, Open from, Device.
- Blok Mermaid di bawah ini: dihasilkan dari data yang sama, tata letaknya otomatis sehingga lebih padat.

Notasi crow's foot. `||` berarti satu dan wajib, `o|` nol atau satu (kunci asing yang boleh kosong), `o{` nol atau banyak. Pada kotak entitas, `PK` kunci utama, `FK` kunci asing (teks miring, diikuti aturan hapusnya), dan `UK` kolom unik. Baris miring di dasar kotak memuat constraint gabungan.

![ERD draw.io](pilihyuk-drawio.png)

```mermaid
erDiagram
    User |o--o{ Product : "added_by"
    User ||--o{ Decision : "user"
    User ||--o{ ProductView : "user"
    User ||--o{ Substitution : "proposed_by"
    User ||--o{ SubstitutionVote : "user"
    User ||--o{ DataCorrection : "submitted_by"
    User |o--o{ DataCorrection : "reviewed_by"
    User ||--o{ Shelf : "owner"
    User ||--o{ SavedShelf : "user"
    User ||--o{ Preference : "user"
    Shelf ||--o{ ShelfItem : "shelf"
    Shelf ||--o{ SavedShelf : "shelf"
    Shelf |o--o{ Decision : "shelf"
    Product ||--o{ ShelfItem : "product"
    Product |o--o{ Decision : "product"
    Product ||--o{ ProductView : "product"
    Product ||--o{ Substitution : "from_product"
    Product ||--o{ Substitution : "to_product"
    Product ||--o{ DataCorrection : "product"
    Substitution ||--o{ SubstitutionVote : "substitution"
    DataCorrection ||--o{ DataCorrectionItem : "correction"
    User {
        int id PK
        string username UK
        string email
        boolean is_staff
        datetime date_joined
    }
    Product {
        int id PK
        string code UK "maks 14, boleh kosong"
        string product_name
        string brand
        string quantity
        string image_url
        string category
        string origin
        string nutrition_grade
        string environmental_grade
        string environmental_grade_estimated
        int nova_group "boleh kosong"
        float energy_kcal_100g
        float proteins_100g
        float fat_100g
        float saturated_fat_100g
        float carbohydrates_100g
        float sugars_100g
        float fiber_100g
        float sodium_100g "gram"
        boolean halal_labeled
        text ingredients_text
        json allergens
        string serving_size
        json categories_tags
        json packaging_tags
        json labels_tags
        json ingredients_analysis_tags
        json misc_tags
        string source "off | manual"
        boolean is_active "soft delete"
        int added_by FK "SET_NULL"
        datetime created_at
        datetime updated_at
        datetime last_synced_at
    }
    ProductView {
        int id PK
        int user_id FK "CASCADE"
        int product_id FK "CASCADE"
        datetime viewed_at
    }
    Shelf {
        int id PK
        string name
        string store_context
        text description
        int owner_id FK "CASCADE"
        boolean is_private
        datetime created_at
        datetime updated_at
    }
    ShelfItem {
        int id PK
        int shelf_id FK "CASCADE"
        int product_id FK "PROTECT"
        datetime added_at
    }
    SavedShelf {
        int id PK
        int user_id FK "CASCADE"
        int shelf_id FK "CASCADE"
        datetime created_at
    }
    Substitution {
        int id PK
        int from_product_id FK "PROTECT"
        int to_product_id FK "PROTECT"
        text reason
        int proposed_by_id FK "CASCADE"
        datetime created_at
    }
    SubstitutionVote {
        int id PK
        int substitution_id FK "CASCADE"
        int user_id FK "CASCADE"
        int value "+1 | -1"
        datetime created_at
    }
    DataCorrection {
        int id PK
        int product_id FK "PROTECT"
        int submitted_by_id FK "CASCADE"
        int reviewed_by_id FK "SET_NULL"
        datetime created_at
        datetime reviewed_at
    }
    DataCorrectionItem {
        int id PK
        int correction_id FK "CASCADE"
        string field_name
        text old_value
        text proposed_value
        string status "pending | approved | rejected"
        text review_note
    }
    Preference {
        int id PK
        int user_id FK "CASCADE"
        string nutrient
        string direction "max | min"
        int weight
    }
    Decision {
        int id PK
        int user_id FK "CASCADE"
        int product_id FK "SET_NULL"
        int shelf_id FK "SET_NULL"
        text note
        datetime created_at
    }
```

## Aturan yang tidak terlihat dari garis

| Hal | Aturan |
|-----|--------|
| Hapus produk | Soft delete lewat `Product.is_active`. `ShelfItem`, `Substitution`, dan `DataCorrection` memakai `PROTECT`, sedangkan `Decision` memakai `SET_NULL` |
| Unik gabungan | `ShelfItem` (shelf, product), `SavedShelf` (user, shelf), `Substitution` (from, to) dengan syarat from berbeda dari to, `SubstitutionVote` (substitution, user), `DataCorrectionItem` (correction, field_name), `Preference` (user, nutrient) |
| Barcode | `Product.code` boleh kosong untuk produk manual dan disimpan sebagai `NULL`, bukan string kosong |
| Nilai yang dihitung | Jumlah suara dan jumlah simpanan shelf dihitung dengan `annotate`, tidak ada kolomnya. Status `DataCorrection` diturunkan dari item-itemnya |
| Tidak disimpan | `environmental_is_estimated` dan tautan halaman produk di Open Food Facts dihitung saat tampil |
| User | Model bawaan Django. Hanya lima kolom yang dipakai aplikasi yang digambar |
