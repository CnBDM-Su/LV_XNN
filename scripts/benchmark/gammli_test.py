# -*- coding: utf-8 -*-
"""
Created on Fri Jun 19 16:21:22 2020

@author: suyu
"""

import numpy as np
import pandas as pd 
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error,roc_auc_score,mean_absolute_error,log_loss
import sys
sys.path.append('../')
from gammli.GAMMLI import GAMMLI
from gammli.DataReader import data_initialize

def gammli( wc, data, meta_info_ori, task_type="Regression", random_state=0, params=None):
    
    train, test = train_test_split(data, test_size=0.2, random_state=0)
    tr_x, tr_Xi, tr_y, tr_idx, te_x, te_Xi, te_y, val_x, val_Xi, val_y, val_idx, meta_info, model_info , sy, sy_t= data_initialize(train, test, meta_info_ori, task_type, 'warm', random_state=0, verbose=True)


    rank = params['rank']
    main_effect_epochs = params['main_effect_epochs']
    interaction_epochs = params['interaction_epochs']
    tuning_epochs = params['tuning_epochs']
    mf_training_iters = params['mf_training_iters']
    u_group_num = params['u_group_num']
    i_group_num = params['i_group_num']
    auto_tune = params['auto_tune']
    best_ratio = params['best_shrinkage']
    best_combine_range = params['best_combination']
    verbose = params['verbose']
    
    if task_type == "Regression":
        cold_mae = []
        cold_rmse = []
        warm_mae = []
        warm_rmse = []
        #gami_mae = []
        #gami_rmse = []
        if auto_tune:
        
            model = GAMMLI(model_info=model_info, meta_info=meta_info, subnet_arch=[8, 16],interact_arch=[20, 10],activation_func=tf.tanh, batch_size=min(500, int(0.2*tr_x.shape[0])), lr_bp=0.001, auto_tune=True,
                           interaction_epochs=interaction_epochs,main_effect_epochs=main_effect_epochs,tuning_epochs=tuning_epochs,loss_threshold_main=0.01,loss_threshold_inter=0.01,
                           verbose=False, early_stop_thres=100,interact_num=10,u_group_num=u_group_num,i_group_num=i_group_num,scale_ratio=1,n_power_iterations=5,n_oversamples=0,
                           mf_training_iters=mf_training_iters,change_mode=True,convergence_threshold=0.001,max_rank=rank,wc=wc,interaction_restrict='intra')
            
            model.fit(tr_x, val_x, tr_y, val_y, tr_Xi, val_Xi, tr_idx, val_idx)
        
            best_ratio = model.final_mf_model.best_ratio
            best_combine_range = model.final_mf_model.best_combine_range
        
        for times in range(10):
            
            print(times)
            
            train, test = train_test_split(data, test_size=0.2, random_state=times)
            tr_x, tr_Xi, tr_y, tr_idx, te_x, te_Xi, te_y, val_x, val_Xi, val_y, val_idx, meta_info, model_info ,sy, sy_t= data_initialize(train, test, meta_info_ori, task_type, 'warm', random_state=0, verbose=False)            

            model = GAMMLI(model_info=model_info, meta_info=meta_info, subnet_arch=[8, 16],interact_arch=[20, 10],activation_func=tf.tanh, batch_size=min(500, int(0.2*tr_x.shape[0])), lr_bp=0.001, auto_tune=False,
                           interaction_epochs=interaction_epochs,main_effect_epochs=main_effect_epochs,tuning_epochs=tuning_epochs,loss_threshold_main=0.01,loss_threshold_inter=0.01,combine_range=best_combine_range,
                           verbose=verbose, early_stop_thres=100,interact_num=10,u_group_num=u_group_num,i_group_num=i_group_num,scale_ratio=best_ratio,n_power_iterations=5,n_oversamples=0,
                           mf_training_iters=mf_training_iters,change_mode=True,convergence_threshold=0.0001,max_rank=rank,wc='warm',interaction_restrict='intra')
    
            model.fit(tr_x, val_x, tr_y, val_y, tr_Xi, val_Xi, tr_idx, val_idx)
            
            pred = model.predict(te_x, te_Xi)
            pred = sy.inverse_transform(pred.reshape(-1,1))
            te_y = sy_t.inverse_transform(te_y.reshape(-1,1))
        
            if wc == 'warm':
                if len([(te_Xi[:,1] != 'cold') & (te_Xi[:,0] != 'cold')])!=1:
                    warm_y = te_y[(te_Xi[:,1] != 'cold') & (te_Xi[:,0] != 'cold')]
                    warm_pred = pred[(te_Xi[:,1] != 'cold') & (te_Xi[:,0] != 'cold')]
                else:
                    warm_y = te_y
                    warm_pred= pred
                warm_mae.append(mean_absolute_error(warm_y,warm_pred))
                warm_rmse.append(mean_squared_error(warm_y,warm_pred)**0.5)

                
            if wc == 'cold':
                try:
                    [(te_Xi[:,1] != 'cold') & (te_Xi[:,0] != 'cold')] != [True]
                    print('no cold samples')
                    continue
                except:
                    cold_y = te_y[(te_Xi[:,1] == 'cold') | (te_Xi[:,0] == 'cold')]
                    cold_pred = pred[(te_Xi[:,1] == 'cold') | (te_Xi[:,0] == 'cold')]

                cold_mae.append(mean_absolute_error(cold_y,cold_pred))
                cold_rmse.append(mean_squared_error(cold_y,cold_pred)**0.5)
                
                
        if wc == 'warm':
            i_result = np.array(['GAMMLI',np.mean(warm_mae),np.mean(warm_rmse),np.std(warm_mae),np.std(warm_rmse)]).reshape(1,-1)
            result = pd.DataFrame(i_result,columns=['model','warm_mae','warm_rmse','std_warm_mae','std_warm_rmse'])
                            
        if wc == 'cold':            
            i_result = np.array(['GAMMLI',np.mean(cold_mae),np.mean(cold_rmse),np.std(cold_mae),np.std(cold_rmse)]).reshape(1,-1)
            result = pd.DataFrame(i_result,columns=['model','cold_mae','cold_rmse','std_cold_mae','std_cold_rmse'])
        
            #gami_mae.append(mean_absolute_error(te_y,model.final_gam_model.predict(te_x)))
            #gami_rmse.append(mean_squared_error(te_y,model.final_gam_model.predict(te_x))**0.5)
        #g_result = np.array(['GAMI',np.mean(gami_mae),np.mean(gami_rmse),np.std(gami_mae),np.std(gami_rmse)]).reshape(1,-1)
        #g_result = pd.DataFrame(g_result,columns=['model','mae','rmse','std_mae','std_rmse'])
    
        return result
    
    if task_type == "Classification":
        cold_auc = []
        cold_logloss = []
        warm_auc = []
        warm_logloss = []
        #gami_auc = []
        #gami_logloss = []
        
        if auto_tune:
        
            model = GAMMLI(wc=wc,model_info=model_info, meta_info=meta_info, subnet_arch=[8, 16],interact_arch=[20, 10],activation_func=tf.tanh, batch_size=min(500, int(0.2*tr_x.shape[0])), lr_bp=0.01, auto_tune=True,
                           interaction_epochs=interaction_epochs,main_effect_epochs=main_effect_epochs,tuning_epochs=tuning_epochs,loss_threshold_main=0.01,loss_threshold_inter=0.01,
                           verbose=False, early_stop_thres=100,interact_num=10,u_group_num=u_group_num,i_group_num=i_group_num,scale_ratio=1,n_power_iterations=5,n_oversamples=0,
                           mf_training_iters=mf_training_iters,change_mode=True,convergence_threshold=0.001,max_rank=rank,interaction_restrict='intra')
    
            model.fit(tr_x, val_x, tr_y, val_y, tr_Xi, val_Xi, tr_idx, val_idx)
        
            best_ratio = model.final_mf_model.best_ratio
            best_combine_range = model.final_mf_model.best_combine_range

        
        for times in range(10):
            
            print(times)
            train, test = train_test_split(data, test_size=0.2, random_state=times)
            tr_x, tr_Xi, tr_y, tr_idx, te_x, te_Xi, te_y, val_x, val_Xi, val_y, val_idx, meta_info, model_info ,sy, sy_t= data_initialize(train, test, meta_info_ori, task_type, 'warm', random_state=0, verbose=False)


            model = GAMMLI(wc='warm',model_info=model_info, meta_info=meta_info, subnet_arch=[8, 16],interact_arch=[20, 10],activation_func=tf.tanh, batch_size=min(500, int(0.2*tr_x.shape[0])), lr_bp=0.001, auto_tune=False,
                           interaction_epochs=interaction_epochs,main_effect_epochs=main_effect_epochs,tuning_epochs=tuning_epochs,loss_threshold_main=0.01,loss_threshold_inter=0.01,combine_range=best_combine_range,
                           verbose=verbose, early_stop_thres=100,interact_num=10,u_group_num=u_group_num,i_group_num=i_group_num,scale_ratio=best_ratio,n_power_iterations=5,n_oversamples=0,
                           mf_training_iters=mf_training_iters,change_mode=True,convergence_threshold=0.001,max_rank=rank,interaction_restrict='intra')
            
            model.fit(tr_x, val_x, tr_y, val_y, tr_Xi, val_Xi, tr_idx, val_idx)
            
            pred = model.predict(te_x, te_Xi)
            
            if wc == 'warm':
                if len([(te_Xi[:,1] != 'cold') & (te_Xi[:,0] != 'cold')])!=1:
                    warm_y = te_y[(te_Xi[:,1] != 'cold') & (te_Xi[:,0] != 'cold')]
                    warm_pred = pred[(te_Xi[:,1] != 'cold') & (te_Xi[:,0] != 'cold')]
                else:
                    warm_y = te_y
                    warm_pred= pred            
                warm_auc.append(roc_auc_score(warm_y,warm_pred))
                warm_logloss.append(log_loss(warm_y,warm_pred))
                
            if wc == 'cold':
        
                try:
                    [(te_Xi[:,1] != 'cold') & (te_Xi[:,0] != 'cold')] != [True]
                    print('no cold samples')
                    continue
                except:
                    cold_y = te_y[(te_Xi[:,1] == 'cold') | (te_Xi[:,0] == 'cold')]
                    cold_pred = pred[(te_Xi[:,1] == 'cold') | (te_Xi[:,0] == 'cold')]

                cold_auc.append(roc_auc_score(cold_y,cold_pred))
                cold_logloss.append(log_loss(cold_y,cold_pred))
                
        if wc == 'warm':
            i_result = np.array(['GAMMLI',np.mean(warm_auc),np.mean(warm_logloss),np.std(warm_auc),np.std(warm_logloss)]).reshape(1,-1)
            result = pd.DataFrame(i_result,columns=['model','warm_auc','warm_logloss','std_warm_auc','std_warm_logloss'])

        if wc == 'cold':            
            i_result = np.array(['GAMMLI',np.mean(cold_auc),np.mean(cold_logloss),np.std(cold_auc),np.std(cold_logloss)]).reshape(1,-1)
            result = pd.DataFrame(i_result,columns=['model','cold_auc','cold_logloss','std_cold_auc','std_cold_logloss'])        

            #gami_auc.append(roc_auc_score(te_y,model.final_gam_model.predict(te_x)))
            #gami_logloss.append(log_loss(te_y,model.final_gam_model.predict(te_x)))
        #g_result = np.array(['GAMI',np.mean(gami_auc),np.mean(gami_logloss),np.std(gami_auc),np.std(gami_logloss)]).reshape(1,-1)
        #g_result = pd.DataFrame(g_result,columns=['model','auc','logloss','std_auc','std_logloss'])
    
        return result


