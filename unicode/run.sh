#!/bin/bash

# --- Configurazione ---

# Il nome dello script Python da eseguire
PYTHON_SCRIPT="detect_unicode_chars.py"

# La lista di stringhe su cui iterare
# Puoi aggiungere o rimuovere stringhe da qui
STRINGS=(
    https://github.com/facebook/react
    https://github.com/vuejs/vue
    https://github.com/angular/angular
    https://github.com/twbs/bootstrap
    https://github.com/jquery/jquery
    https://github.com/freeCodeCamp/freeCodeCamp
    https://github.com/nodejs/node
    https://github.com/npm/cli
    https://github.com/tensorflow/tfjs
    https://github.com/d3/d3
    https://github.com/chartjs/Chart.js
    https://github.com/lodash/lodash
    https://github.com/sveltejs/svelte
    https://github.com/vercel/next.js
    https://github.com/vitejs/vite
    https://github.com/nestjs/nest
    https://github.com/preactjs/preact
    https://github.com/pmndrs/zustand
    https://github.com/fabian-hiller/valibot
    https://github.com/zloirock/core-js
    https://github.com/expressjs/express
    https://github.com/koajs/koa
    https://github.com/hapijs/hapi
    https://github.com/socketio/socket.io
    https://github.com/sequelize/sequelize
    https://github.com/typeorm/typeorm
    https://github.com/prisma/prisma
    https://github.com/knex/knex
    https://github.com/jestjs/jest
    https://github.com/mochajs/mocha
    https://github.com/chaijs/chai
    https://github.com/visionmedia/supertest
    https://github.com/cypress-io/cypress
    https://github.com/yargs/yargs
    https://github.com/ajaxorg/ace
    https://github.com/quilljs/quill
    https://github.com/microsoft/monaco-editor
    https://github.com/ianstormtaylor/slate
    https://github.com/janl/mustache.js
    https://github.com/cheeriojs/cheerio
    https://github.com/visionmedia/superagent
    https://github.com/nock/nock
    https://github.com/shoelace-style/shoelace
    https://github.com/oclif/oclif
    https://github.com/infinitered/gluegun
    https://github.com/mobxjs/mobx
    https://github.com/davidkpiano/xstate
    https://github.com/vuejs/pinia
    https://github.com/apexcharts/apexcharts.js
    https://github.com/ecomfe/echarts
    https://github.com/antvis/g2
    https://github.com/plotly/plotly.js
    https://github.com/cytoscape/cytoscape.js
    https://github.com/jacomyal/sigma.js
    https://github.com/antvis/g6
    https://github.com/vega/vega
    https://github.com/vega/vega-lite
    https://github.com/babel/babel
    https://github.com/eslint/eslint
    https://github.com/typicode/json-server
    https://github.com/sweetalert2/sweetalert2
    https://github.com/jorgebucaran/hyperapp
    https://github.com/developit/mitt

    # https://github.com/molefrog/wouter
    # https://github.com/remeda/remeda
    # https://github.com/ianstormtaylor/superstruct
    # https://github.com/omgovich/colord
    # https://github.com/vercel/ms
    # https://github.com/redom/redom
    # https://github.com/frejs/fre
    # https://github.com/vanjs-org/van
    # https://github.com/ai/nanoid
    # https://github.com/elbywan/wretch
    # https://github.com/selfrefactor/rambda
    # https://github.com/marpple/FxTS
    # https://github.com/davidmerfield/randomColor
    # https://github.com/nanostores/nanostores
    # https://github.com/developit/unistore
    # https://github.com/preactjs/signals
    # https://github.com/tj/commander.js
    # https://github.com/SBoudrias/Inquirer.js
    # https://github.com/chalk/chalk
    # https://github.com/sindresorhus/ora
    # https://github.com/juliangarnier/anime
    # https://github.com/visjs/vis-network
    # https://github.com/vadimdemedes/ink
    # https://github.com/pmndrs/jotai
    # https://github.com/dc-js/dc.js
    # https://github.com/nhn/tui.chart
    # https://github.com/bpmn-io/diagram-js
    # https://github.com/graphology/graphology
)

# --- Esecuzione ---

echo "Inizio esecuzione del comando Python per ogni stringa..."
echo "Script Python: ${PYTHON_SCRIPT}"
echo "--------------------------------------------------"

# Loop attraverso ogni stringa nell'array
for s in "${STRINGS[@]}"; do
    echo "Esecuzione per la stringa: \"$s\""
    # Esegue il comando python, passando la stringa come argomento
    # Le virgolette attorno a "$s" sono importanti per gestire stringhe con spazi
    python3 $PYTHON_SCRIPT $s -e js
    
    # Puoi aggiungere qui ulteriori comandi o logica
    # Ad esempio, per controllare lo stato di uscita del comando Python:
    # if [ $? -ne 0 ]; then
    #     echo "Errore durante l'esecuzione per \"$s\""
    # fi
    echo "--------------------------------------------------"
done

echo "Esecuzione completata!"
