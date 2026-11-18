import re
from pathlib import Path
import pandas as pd

def clean_number(value):
    if pd.isna(value): return None
    text = str(value).strip().replace(",", "").replace("₹", "").replace("%", "")
    text = re.sub(r"[^\d.]", "", text)
    try: return float(text) if text else None
    except ValueError: return None

class ProductRetriever:
    """Dataset-first retrieval: hard constraints filter; descriptive preferences rank."""
    def __init__(self, csv_path):
        self.path = Path(csv_path)
        self.df = pd.DataFrame()
        self.ready = False
        self.status = "Dataset not found"
        self._load()

    @property
    def product_count(self):
        return len(self.df)

    def _load(self):
        if not self.path.exists():
            self.status = f"Missing {self.path.name} — add the Kaggle CSV beside app.py"
            return
        try:
            df = pd.read_csv(self.path).fillna("")
            required = ["product_id","product_name","category","discounted_price","actual_price",
                        "discount_percentage","rating","rating_count","about_product","img_link","product_link"]
            for col in required:
                if col not in df: df[col] = ""
            df["price_num"] = df["discounted_price"].apply(clean_number)
            df["actual_price_num"] = df["actual_price"].apply(clean_number)
            df["rating_num"] = df["rating"].apply(clean_number)
            df["rating_count_num"] = df["rating_count"].apply(clean_number)
            df["category_text"] = df["category"].astype(str).str.lower()
            df["name_text"] = df["product_name"].astype(str).str.lower()
            df["search_text"] = (df["name_text"]+" "+df["category_text"]+" "+df["about_product"].astype(str).str.lower())
            df = df.drop_duplicates(subset=["product_id"], keep="first")
            self.df, self.ready = df, True
            self.status = f"Kaggle CSV loaded · {len(df)} unique products"
        except Exception as exc:
            self.status = f"Could not read dataset: {exc}"

    @staticmethod
    def _value(state, key):
        item = state.get(key, {})
        return item.get("value") if isinstance(item, dict) else item

    def search(self, state, limit=None):
        if not self.ready or self.df.empty: return []
        df = self.df.copy()
        category = str(self._value(state,"category") or "").lower().strip()
        # Normalize conversational category phrases to the dataset's taxonomy.
        # Classify audio before phones: the substring "phone" occurs inside
        # "earphone", so naive substring matching misclassifies earphones as phones.
        audio_category = bool(re.search(r"\b(earphones?|earbuds?|headphones?|headsets?)\b", category))
        phone_category = bool(re.search(r"\b(phones?|smartphones?|mobiles?|iphone)\b", category))
        if audio_category:
            df = df[df["category_text"].str.contains(r"headphones|earbuds", regex=True, na=False)]
        elif phone_category or re.search(r"\bgalaxy\s+s\s*series\b", category):
            df = df[df["category_text"].str.contains(r"smartphones|mobiles", regex=True, na=False)]
        elif category:
            # Exact taxonomy token or title match, not every token in the whole phrase.
            toks = [t for t in re.findall(r"[a-z0-9]+", category) if len(t)>2]
            candidate = pd.Series(False,index=df.index)
            for token in toks:
                candidate |= df["category_text"].str.contains(re.escape(token),na=False) | df["name_text"].str.contains(re.escape(token),na=False)
            if candidate.any(): df=df[candidate]

        # Explicit brand constraint. Do not require whole natural-language phrase.
        brand = str(self._value(state,"brand_preference") or "").lower().strip()
        if brand and brand not in {"any","any brand","no preference","open to anything"}:
            df = df[df["search_text"].str.contains(r"\b"+re.escape(brand)+r"\b",regex=True,na=False)]

        # Samsung Galaxy S-series is a model-series constraint within smartphones.
        if "galaxy s" in category or "s series" in category or any(
            "galaxy s" in str(x.get("value","")).lower() or "s series" in str(x.get("value","")).lower()
            for x in state.get("features",[]) if isinstance(x,dict)
        ):
            df = df[df["name_text"].str.contains(r"\bgalaxy\s+s\d|galaxy\s+s\d{1,2}\s",regex=True,na=False)]

        minp=self._value(state,"budget_min"); maxp=self._value(state,"budget_max")
        if minp is not None: df=df[df["price_num"].notna() & (df["price_num"]>=float(minp))]
        if maxp is not None: df=df[df["price_num"].notna() & (df["price_num"]<=float(maxp))]
        rating=self._value(state,"min_rating")
        if rating is not None: df=df[df["rating_num"].notna() & (df["rating_num"]>=float(rating))]
        count=self._value(state,"min_rating_count")
        if count is not None: df=df[df["rating_count_num"].notna() & (df["rating_count_num"]>=float(count))]

        # Soft preferences are used to rank, never silently discard otherwise valid records.
        df=df.copy(); df["_relevance"]=0
        synonyms={
            "anc":["anc","active noise cancellation","active noise cancelling"],
            "noise cancelling":["noise cancelling","noise cancellation","anc"],
            "wireless":["wireless","bluetooth","truly wireless","tws"],
            "bluetooth":["bluetooth","wireless","tws"],
            "microphone":["microphone","mic","enc","calling"],
            "calls":["microphone","mic","enc","calling"],
            "music":["music","audio","bass","sound"],
            "multipurpose":["microphone","mic","music","audio","bluetooth"],
        }
        prefs=[]
        for item in state.get("features",[]) if isinstance(state.get("features",[]),list) else []:
            prefs.append(item.get("value","") if isinstance(item,dict) else str(item))
        purpose=self._value(state,"purpose")
        if purpose: prefs += re.findall(r"[a-z]+",str(purpose).lower())
        # Phrase tokens from the original conversational category, e.g. "Samsung Galaxy S series".
        if category: prefs += ["galaxy s series"] if "galaxy s" in category or "s series" in category else []
        for pref in set(prefs):
            pref=str(pref).lower().strip()
            if not pref or pref in {"call","calls","music","multi-purpose","multipurpose"}: continue
            variants=synonyms.get(pref,[pref])
            hit=pd.Series(False,index=df.index)
            for term in variants: hit |= df["search_text"].str.contains(re.escape(term),na=False)
            df["_relevance"] += hit.astype(int)*2
        if "call" in str(purpose).lower():
            df["_relevance"] += df["search_text"].str.contains(r"microphone|mic\b|enc\b|calling",regex=True,na=False).astype(int)*2
        df=df.sort_values(["_relevance","rating_num","rating_count_num"],ascending=[False,False,False],na_position="last")

        # Return every match by default. UI can scroll; no arbitrary top-6 truncation.
        if limit is not None: df=df.head(limit)
        products=[]
        for _,r in df.iterrows():
            def num(v): return float(v) if pd.notna(v) and v!="" else None
            products.append({
                "id":str(r["product_id"]),"name":str(r["product_name"]),"category":str(r["category"]),
                "price":num(r["price_num"]),"actual_price":num(r["actual_price_num"]),
                "discount":str(r["discount_percentage"]),"rating":num(r["rating_num"]),
                "rating_count":num(r["rating_count_num"]),"description":str(r["about_product"]),
                "image":str(r["img_link"]),"link":str(r["product_link"]),
                "evidence":{"price":"discounted_price","rating":"rating","review_volume":"rating_count",
                            "features":"product_name/category/about_product text",
                            "brand":"matched in product name/description"}
            })
        return products
