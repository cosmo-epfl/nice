import os
import json
import copy

# cutting notebooks
def split(name, destination):
    with open("tutorials/{}".format(name), "r") as f:
        notebook = json.load(f)
        
    before_collapsible = copy.deepcopy(notebook)
    before_collapsible['cells'] = before_collapsible['cells'][0:2]

    collapsible = copy.deepcopy(notebook)
    collapsible['cells'] = [collapsible['cells'][2]]

    after_collapsible = copy.deepcopy(notebook)
    after_collapsible['cells'] = after_collapsible['cells'][3:]
    
    clean_name = name.strip().split('.')[0]
    with open("{}/{}_before_collapsible.ipynb".format(destination,
                                                      clean_name), "w") as f:
        json.dump(before_collapsible, f)
    
    with open("{}/{}_collapsible.ipynb".format(destination,
                                                      clean_name), "w") as f:
        json.dump(collapsible, f)


    with open("{}/{}_after_collapsible.ipynb".format(destination,
                                                      clean_name), "w") as f:
        json.dump(after_collapsible, f)
        
os.system("mkdir docs/cutted")       
split('calculating_covariants.ipynb', 'docs/cutted/')
split('getting_insights_about_the_model.ipynb', 'docs/cutted/')



# converting notebooks to rst 
os.chdir('docs/cutted/')
names = [name for name in os.listdir('.') if name.endswith('.ipynb')]

for name in names:
    dir_name = name.split('.')[0]    
    os.system("mkdir {}".format(dir_name))
    os.system("cp {} {}/".format(name, dir_name))
    os.chdir(dir_name)
    os.system('jupyter nbconvert --to rst {}'.format(name))
    os.chdir('../')
    
os.chdir('../..')

os.system("rm -r ../build/*")
os.chdir("./docs")
os.system("sphinx-apidoc -f -o . ../nice")
os.system("make html")
os.chdir("../")
os.system("git checkout -f gh-pages")
os.system("git rm -r *")
os.system("cp -r ../build/html/* .")
with open(".nojekyll", "w") as f:
    pass

os.system("git add *")
os.system("git add .nojekyll")
os.system("git commit -m 'automatic docs build'")
os.system("git push")
os.system("git checkout master")
