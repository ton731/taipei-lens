
### Start Service
```sh
# Frontend
cd frontend/
npm run dev

# Backend
cd backend/
bash start.sh
```


### Preprocessing
```sh
### Building
python preprocess/building/1_print_geojson.py
python preprocess/building/2_visualize_different_geojson.py
python preprocess/building/3_merge_geojson.py
python preprocess/building/4_visualize_merged_geojson.py

### Social Vulnerability
python preprocess/social_vulnerability/1_extract_population_age.py
python preprocess/social_vulnerability/2_extract_low_income.py
python preprocess/social_vulnerability/3_extract_live_alone_elderly.py
python preprocess/social_vulnerability/4_merge_district_geojson.py
```