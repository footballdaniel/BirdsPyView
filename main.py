from streamlit import bootstrap

real_script = "birdspyview.py"

bootstrap.run(real_script, f'run.py {real_script}', [])